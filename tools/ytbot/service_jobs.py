"""Durable idempotent job admission; lost external actors are never blindly replayed."""

from __future__ import annotations
import contextlib
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from . import channels, config
from .accounts_store import AccountStore, private_directory, read_private, write_private

STATES = {"accepted", "running", "completed", "failed", "uncertain"}


def canonical_id(value: str) -> str:
    parsed = uuid.UUID(value)
    if str(parsed) != value:
        raise ValueError("operation ID must be a canonical UUID")
    return value


def jobs_root() -> Path:
    return private_directory(config.ROOT / ".local" / "ytbot-service" / "jobs")


@contextlib.contextmanager
def channel_lock(slug: str):
    channels.get(slug)
    directory = private_directory(
        config.ROOT / ".local" / "ytbot-service" / "channel-locks"
    )
    descriptor = os.open(
        directory / (slug + ".lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
    )
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("this channel already has an active batch") from None
        yield
    finally:
        os.close(descriptor)


def process_identity(pid: int) -> str | None:
    try:
        text = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if text[0] == "Z" else text[19]
    except (OSError, IndexError):
        return None


def public(record: dict) -> dict:
    request = record["request"]
    return {
        "schema_version": 1,
        "operation_id": record["operation_id"],
        "state": record["state"],
        "channel": request["channel"],
        "account": request["account"],
        "count": request["count"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "summary": str(record.get("summary", ""))[:1000],
        "error_code": record.get("error_code"),
        "result": record.get(
            "result", {"scheduled_count": 0, "failed_count": 0, "runs": []}
        ),
    }


@contextlib.contextmanager
def job_lock(operation_id: str):
    descriptor = os.open(
        jobs_root() / (canonical_id(operation_id) + ".lock"),
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def status(operation_id: str) -> dict:
    with job_lock(operation_id):
        return _status(operation_id)


def _status(operation_id: str) -> dict:
    path = jobs_root() / (canonical_id(operation_id) + ".json")
    record = read_private(path)
    if not record:
        raise ValueError("operation is not known")
    lost = record["state"] == "running" and process_identity(
        record.get("pid", 0)
    ) != record.get("process_identity")
    unstarted = (
        record["state"] == "accepted" and time.time() - record["created_at"] > 30
    )
    if lost or unstarted:
        record.update(
            state="uncertain",
            updated_at=int(time.time()),
            error_code="actor_lost",
            summary="Execution status is uncertain. Inspect private records; automatic replay is fenced.",
        )
        write_private(path, record)
    return public(record)


class SetupUnavailable(RuntimeError):
    """No media actor was launched because the separate user manager is unavailable."""


ACTOR_ENVIRONMENT = {
    "HOME",
    "USER",
    "LOGNAME",
    "PATH",
    "LANG",
    "LC_ALL",
    "TZ",
    "PYTHONPATH",
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "XAUTHORITY",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "CUDA_VISIBLE_DEVICES",
    "CUDA_DEVICE_ORDER",
    "NVIDIA_VISIBLE_DEVICES",
    "TORCH_CUDA_ARCH_LIST",
}


def launch_actor(command, *, cwd, env, **_ignored):
    """Move heavy work outside the 512 MiB coordinator worker's systemd cgroup."""
    if not shutil.which("systemd-run") or not shutil.which("systemctl"):
        raise SetupUnavailable("a systemd user manager is required for media jobs")
    try:
        ready = subprocess.run(
            ["/usr/bin/systemctl", "--user", "show-environment"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        raise SetupUnavailable(
            "a systemd user manager is required for media jobs"
        ) from None
    if ready.returncode != 0:
        raise SetupUnavailable("the systemd user manager is unavailable")
    operation = canonical_id(command[-1])
    arguments = [
        "/usr/bin/systemd-run",
        "--user",
        "--quiet",
        "--collect",
        "--service-type=exec",
        "--unit=youtubebot-" + operation,
        "--working-directory=" + str(cwd),
        "--property=MemoryHigh=12G",
        "--property=MemoryMax=16G",
        "--property=CPUQuota=200%",
        "--property=TasksMax=256",
        "--property=RuntimeMaxSec=12h",
        "--property=Restart=no",
        "--property=KillMode=control-group",
        "--property=TimeoutStopSec=15",
        "--property=UMask=0077",
        "--property=StandardOutput=null",
        "--property=StandardError=null",
        "--",
        "/usr/bin/env",
        "-i",
    ]
    # env -i also excludes credentials imported into the user manager itself.
    arguments.extend(
        key + "=" + value
        for key, value in sorted(env.items())
        if key in ACTOR_ENVIRONMENT
    )
    arguments.extend(command)
    return subprocess.run(
        arguments,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        timeout=15,
        check=True,
    )


def submit(
    operation_id: str,
    channel: str,
    account: str,
    count: int,
    approved_schedule: bool,
    *,
    launcher=launch_actor,
    store: AccountStore | None = None,
) -> dict:
    operation_id = canonical_id(operation_id)
    channels.get(channel)
    store = store or AccountStore()
    store.account(account)
    if not 1 <= count <= 10 or not approved_schedule:
        raise ValueError(
            "count must be 1..10 and explicit scheduled-publication permission is required"
        )
    request = {
        "channel": channel,
        "account": account,
        "count": count,
        "approved_schedule": True,
    }
    fingerprint = hashlib.sha256(
        json.dumps(request, sort_keys=True).encode()
    ).hexdigest()
    path = jobs_root() / (operation_id + ".json")
    record = {
        "schema": 1,
        "operation_id": operation_id,
        "request": request,
        "fingerprint": fingerprint,
        "state": "accepted",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "pid": None,
        "process_identity": None,
        "error_code": None,
        "summary": "Video batch durably accepted; not yet finished.",
    }
    with job_lock(operation_id):
        previous = read_private(path)
        if previous:
            if previous.get("fingerprint") != fingerprint:
                raise ValueError("operation ID belongs to a different request")
            return _status(operation_id)
        write_private(path, record, exclusive=True)
    # An admission record always exists before a process or external browser action.
    environment = {
        key: value
        for key, value in os.environ.items()
        if not any(
            word in key.upper() for word in ("TOKEN", "PASSWORD", "SECRET", "API_KEY")
        )
    }
    environment["PYTHONPATH"] = str(config.ROOT)
    try:
        launcher(
            [
                sys.executable,
                "-m",
                "tools.ytbot.service",
                "_execute",
                "--operation-id",
                operation_id,
            ],
            cwd=config.ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except (SetupUnavailable, OSError, subprocess.SubprocessError) as error:
        with job_lock(operation_id):
            current = read_private(path)
            if current["state"] != "accepted":
                record = current
            else:
                unavailable = isinstance(error, SetupUnavailable)
                record.update(
                    state="failed" if unavailable else "uncertain",
                    updated_at=int(time.time()),
                    error_code="setup_unavailable"
                    if unavailable
                    else "launch_uncertain",
                    summary="A separate systemd user media service is required; no video actor was launched."
                    if unavailable
                    else "Job admission retained; process launch needs inspection before any retry.",
                )
                write_private(path, record)
    return public(record)


class BoundedLog:
    def __init__(self, stream, limit=10 * 1024 * 1024):
        self.stream = stream
        self.remaining = limit

    def write(self, value):
        raw = value.encode("utf-8", errors="replace")[: self.remaining]
        self.remaining -= len(raw)
        self.stream.write(raw)
        return len(value)

    def flush(self):
        self.stream.flush()


def execute(operation_id: str) -> None:
    operation_id = canonical_id(operation_id)
    directory = jobs_root()
    path = directory / (operation_id + ".json")
    # This marker intentionally survives a crash; invoking the same job cannot repeat an uncertain upload.
    with job_lock(operation_id):
        record = read_private(path)
        if not record or record["state"] != "accepted":
            return
        try:
            fence = os.open(
                directory / (operation_id + ".execution"),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
        except FileExistsError:
            return
        os.fsync(fence)
        os.close(fence)
        record.update(
            state="running",
            pid=os.getpid(),
            process_identity=process_identity(os.getpid()),
            updated_at=int(time.time()),
            summary="Video batch is running.",
        )
        write_private(path, record)
    log_descriptor = os.open(
        directory / (operation_id + ".log"),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(log_descriptor, "wb") as stream:
        writer = BoundedLog(stream)
        with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
            try:
                from .batch import run_batch
                from .library import runs

                request = record["request"]
                store = AccountStore()
                channels.apply(request["channel"])
                with store.profile_lock(request["account"]):
                    with channel_lock(request["channel"]):
                        store.activate(request["account"])
                        before = {
                            p.parent.name: p.stat().st_mtime_ns
                            for p in config.RUNS.glob("*/record.json")
                        }
                        failures = run_batch(request["count"])
                        changed = {
                            p.parent.name
                            for p in config.RUNS.glob("*/record.json")
                            if p.stat().st_mtime_ns != before.get(p.parent.name)
                        }
                        results = [
                            item
                            for item in runs(request["channel"], 100)
                            if item["id"] in changed
                        ][: request["count"]]
                scheduled = sum(item["state"] == "scheduled" for item in results)
                failed = max(len(failures), request["count"] - scheduled)
                record.update(
                    state="failed" if failed else "completed",
                    error_code="batch_failed" if failed else None,
                    summary=f"Batch finished: {scheduled} scheduled video(s), {failed} incomplete or failed item(s).",
                    result={
                        "scheduled_count": scheduled,
                        "failed_count": failed,
                        "runs": results,
                    },
                )
            except BaseException:
                record.update(
                    state="failed",
                    error_code="execution_failed",
                    summary="Batch failed; inspect private job logs and existing resumable records.",
                )
            finally:
                record["updated_at"] = int(time.time())
                with job_lock(operation_id):
                    write_private(path, record)
