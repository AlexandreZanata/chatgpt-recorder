"""Private account registry. Tokens and browser profiles never appear in public records."""

from __future__ import annotations
import contextlib
import fcntl
import json
import os
import re
from pathlib import Path
from . import config

IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]{0,47}\Z")


def private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir() or path.stat().st_mode & 0o077:
        raise ValueError("a private real directory with mode 0700 is required")
    return path


def write_private(path: Path, value: dict, *, exclusive: bool = False) -> None:
    private_directory(path.parent)
    data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    if exclusive:
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    else:
        temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
        descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_private(path: Path, default=None):
    if not path.exists():
        return default
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor) as stream:
        metadata = os.fstat(stream.fileno())
        import stat

        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_mode & 0o077
            or metadata.st_size > 1024 * 1024
        ):
            raise ValueError(
                "private state requires a regular 0600 file within the size limit"
            )
        return json.load(stream)


class AccountStore:
    def __init__(self, root: Path | None = None):
        self.root = private_directory(root or config.ROOT / ".local" / "accounts")
        self.path = self.root / "registry.json"

    def load(self) -> dict:
        data = read_private(self.path, {"schema": 1, "accounts": {}, "bindings": {}})
        if (
            data.get("schema") != 1
            or not isinstance(data.get("accounts"), dict)
            or not isinstance(data.get("bindings"), dict)
        ):
            raise ValueError("unsupported account registry")
        return data

    @contextlib.contextmanager
    def transaction(self):
        path = self.root / "registry.lock"
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            data = self.load()
            yield data
            write_private(self.path, data)
        finally:
            os.close(descriptor)

    def create(self, identifier: str, label: str) -> dict:
        if (
            not IDENTIFIER.fullmatch(identifier)
            or identifier == "legacy"
            or not label.strip()
            or len(label) > 100
        ):
            raise ValueError(
                "use a unique lowercase account ID and a short display name"
            )
        with self.transaction() as data:
            if identifier in data["accounts"] or len(data["accounts"]) >= 20:
                raise ValueError("account already exists or registry is full")
            used = {account["cdp_port"] for account in data["accounts"].values()}
            port = next(port for port in range(9301, 9321) if port not in used)
            data["accounts"][identifier] = {
                "id": identifier,
                "label": label.strip(),
                "cdp_port": port,
            }
        private_directory(self.profile(identifier))
        return self.account(identifier)

    def account(self, identifier: str) -> dict:
        if identifier == "legacy":
            return {"id": "legacy", "label": "Existing bot session", "cdp_port": 9300}
        if not IDENTIFIER.fullmatch(identifier):
            raise ValueError("invalid account ID")
        account = self.load()["accounts"].get(identifier)
        if account is None:
            raise ValueError("account is not registered")
        return dict(account)

    def profile(self, identifier: str) -> Path:
        self.account(identifier)
        if identifier == "legacy":
            return (
                config.LEGACY_PROFILE
                if config.LEGACY_PROFILE.is_dir()
                else config.DATA / "profile"
            )
        return self.root / "browser" / identifier

    def public_accounts(self) -> list[dict]:
        records = [self.account("legacy"), *self.load()["accounts"].values()]
        return [
            {
                "id": item["id"],
                "label": item["label"],
                "browser_configured": (self.profile(item["id"]) / "Default").is_dir(),
                "oauth_connected": (
                    self.root / "oauth" / (item["id"] + ".json")
                ).is_file(),
            }
            for item in records
        ]

    def bind(self, channel_slug: str, identifier: str, channel_id: str) -> None:
        from .channels import get

        expected = get(channel_slug).channel_id
        self.account(identifier)
        if channel_id != expected:
            raise ValueError(
                "Google channel identity does not match the selected profile"
            )
        with self.transaction() as data:
            data["bindings"][channel_slug] = {
                "account_id": identifier,
                "channel_id": channel_id,
            }

    def activate(self, identifier: str) -> None:
        account = self.account(identifier)
        config.PROFILE = self.profile(identifier)
        config.CDP_PORT = account["cdp_port"]
        config.ACCOUNT_ID = identifier

    @contextlib.contextmanager
    def profile_lock(self, identifier: str):
        self.account(identifier)
        directory = private_directory(self.root / "locks")
        descriptor = os.open(
            directory / (identifier + ".lock"),
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
            0o600,
        )
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError(
                    "this account is busy; finish its sign-in or batch first"
                ) from None
            yield
        finally:
            os.close(descriptor)
