"""Hermetic account/channel, OAuth and durable service contracts; no real accounts."""

from __future__ import annotations
import base64
import concurrent.futures
import hashlib
import json
import stat
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from unittest.mock import Mock, patch
from tools.ytbot import channels, config, library, oauth, service_jobs
from tools.ytbot.account import verify_channel_identity
from tools.ytbot.accounts_store import AccountStore, read_private, write_private


class AccountFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = patch.object(config, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        previous = (config.PROFILE, config.CDP_PORT, config.ACCOUNT_ID)
        self.addCleanup(
            lambda: (
                setattr(config, "PROFILE", previous[0]),
                setattr(config, "CDP_PORT", previous[1]),
                setattr(config, "ACCOUNT_ID", previous[2]),
            )
        )
        self.store = AccountStore()
        self.store.create("work", "Work")

    def tearDown(self):
        channels.apply("fallem-prince")


class AccountContracts(AccountFixture):
    def test_independent_private_profiles_and_explicit_channel_binding(self):
        self.store.create("personal", "Personal")
        self.assertNotEqual(self.store.profile("work"), self.store.profile("personal"))
        self.assertNotEqual(
            self.store.account("work")["cdp_port"],
            self.store.account("personal")["cdp_port"],
        )
        self.assertEqual(stat.S_IMODE(self.store.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.store.profile("work").stat().st_mode), 0o700)
        channel = channels.get("fallem-prince")
        with self.assertRaises(ValueError):
            self.store.bind(channel.slug, "work", "UC" + "x" * 22)
        self.store.bind(channel.slug, "work", channel.channel_id)
        self.assertEqual(
            self.store.load()["bindings"][channel.slug]["account_id"], "work"
        )
        self.assertNotIn("profile", json.dumps(self.store.public_accounts()))

    def test_account_ids_permissions_and_symlinks_are_denied(self):
        for identifier in ["../other", "UPPER", "", "legacy"]:
            with self.assertRaises(ValueError):
                self.store.create(identifier, "Unsafe")
        self.store.path.chmod(0o644)
        with self.assertRaises(ValueError):
            self.store.load()
        self.store.path.chmod(0o600)
        self.store.path.unlink()
        self.store.path.symlink_to(self.root / "outside")
        (self.root / "outside").write_text("{}")
        with self.assertRaises(OSError):
            self.store.load()

    def test_simultaneous_account_control_is_rejected(self):
        with self.store.profile_lock("work"):
            with self.assertRaises(ValueError):
                with self.store.profile_lock("work"):
                    pass
        with self.store.profile_lock("work"):
            pass

    def test_channel_identity_is_never_inferred_from_display_name(self):
        expected = channels.get("zaflas").channel_id
        self.assertEqual(
            verify_channel_identity(
                "https://studio.youtube.com/channel/" + expected + "/videos", expected
            ),
            expected,
        )
        for url in [
            "https://studio.youtube.com/channel/UC" + "x" * 22 + "/videos",
            "https://studio.youtube.com.evil/channel/" + expected,
            "http://studio.youtube.com/channel/" + expected,
        ]:
            with self.assertRaises(RuntimeError):
                verify_channel_identity(url, expected)

    def test_run_index_preserves_title_schedule_and_redacts_private_urls(self):
        with patch.object(config, "DATA", self.root / "data"):
            channels.apply("fallem-prince")
            run = config.RUNS / "example"
            run.mkdir(parents=True)
            (run / "record.json").write_text(
                json.dumps(
                    {
                        "topic": "Exact topic",
                        "stages": [{"status": "error", "detail": "private chat url"}],
                    }
                )
            )
            (run / "metadata.json").write_text(
                json.dumps({"title": "Exact selected title", "private": "never return"})
            )
            (run / "upload.json").write_text(
                json.dumps(
                    {
                        "videoId": "fixtureVideo",
                        "slot": "2026-11-14 12:00",
                        "scheduled": True,
                        "url": "private url",
                    }
                )
            )
            result = library.runs("fallem-prince", 20)[0]
            self.assertEqual(result["title"], "Exact selected title")
            self.assertEqual(result["video_id"], "fixtureVideo")
            self.assertEqual(result["state"], "scheduled")
            self.assertNotIn("private", json.dumps(result))
            (run / "upload.json").unlink()
            self.assertEqual(library.runs("fallem-prince")[0]["state"], "error")

    def test_browser_preferences_preserve_existing_profile_settings(self):
        from tools.ytbot import runtime

        profile = self.root / "profile"
        (profile / "Default").mkdir(parents=True)
        preferences = profile / "Default/Preferences"
        preferences.write_text(json.dumps({"keep_existing": True}))
        with (
            patch.object(config, "PROFILE", profile),
            patch.object(config, "ACCOUNT_ID", "work"),
        ):
            runtime._write_preferences()
        self.assertTrue(json.loads(preferences.read_text())["keep_existing"])

    def test_profile_process_selection_uses_exact_arguments_and_rejects_foreign_cdp(
        self,
    ):
        from tools.ytbot import runtime

        profile = str(config.PROFILE)
        processes = [
            (
                101,
                [
                    b"chrome",
                    f"--user-data-dir={profile}".encode(),
                    b"--remote-debugging-port=9300",
                ],
            ),
            (
                102,
                [
                    b"chrome",
                    f"--user-data-dir={profile}-other".encode(),
                    b"--remote-debugging-port=9301",
                ],
            ),
        ]
        with patch.object(runtime, "_browser_processes", return_value=iter(processes)):
            self.assertEqual(runtime._chrome_pids(), [101])
        with patch.object(runtime, "_browser_processes", return_value=iter(processes)):
            runtime._assert_cdp_owner()
        processes[1][1][-1] = b"--remote-debugging-port=9300"
        with patch.object(runtime, "_browser_processes", return_value=iter(processes)):
            with self.assertRaises(RuntimeError):
                runtime._assert_cdp_owner()


class OAuthContracts(AccountFixture):
    def client(self):
        client = self.root / "client.json"
        client.write_text(
            json.dumps(
                {
                    "installed": {
                        "client_id": "fixture.apps.googleusercontent.com",
                        "client_secret": "synthetic-client-only",
                    }
                }
            )
        )
        client.chmod(0o600)
        return client

    def test_pkce_csrf_loopback_and_readonly_channel_discovery(self):
        callbacks = []
        exchange_calls = []

        def opener(url):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            self.assertEqual(params["code_challenge_method"], ["S256"])
            self.assertNotIn("youtube.upload", params["scope"][0])
            redirect = params["redirect_uri"][0]
            self.assertTrue(redirect.startswith("http://127.0.0.1:"))

            def callback():
                try:
                    urllib.request.urlopen(
                        redirect + "?state=wrong&code=not-a-real-code", timeout=3
                    )
                except urllib.error.HTTPError as error:
                    self.assertEqual(error.code, 400)
                with urllib.request.urlopen(
                    redirect
                    + "?"
                    + urllib.parse.urlencode(
                        {"state": params["state"][0], "code": "synthetic-code"}
                    ),
                    timeout=3,
                ) as response:
                    self.assertEqual(response.status, 200)

            thread = threading.Thread(target=callback)
            callbacks.append((thread, params))
            thread.start()
            return True

        def exchange(url, **kwargs):
            exchange_calls.append((url, kwargs))
            if url == oauth.TOKEN:
                return {
                    "access_token": "synthetic-access-token",
                    "refresh_token": "synthetic-refresh-token",
                }
            return {
                "items": [
                    {
                        "id": channels.get("fallem-prince").channel_id,
                        "snippet": {"title": "Fixture channel"},
                    }
                ]
            }

        result = oauth.connect(
            self.store, "work", self.client(), opener=opener, exchange=exchange
        )
        for thread, params in callbacks:
            thread.join(timeout=5)
        verifier = exchange_calls[0][1]["data"]["code_verifier"]
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        self.assertEqual(challenge, callbacks[0][1]["code_challenge"][0])
        self.assertEqual(len(result), 1)
        token = self.store.root / "oauth/work.json"
        self.assertEqual(stat.S_IMODE(token.stat().st_mode), 0o600)
        self.assertNotIn(
            "synthetic-access-token", json.dumps(self.store.public_accounts())
        )

    def test_cancelled_browser_and_unsafe_client_file_do_not_store_tokens(self):
        client = self.client()
        client.chmod(0o644)
        with self.assertRaises(ValueError):
            oauth.client_settings(client)
        client.chmod(0o600)
        with self.assertRaises(ValueError):
            oauth.connect(self.store, "work", client, opener=lambda _url: False)
        self.assertFalse((self.store.root / "oauth/work.json").exists())


class ServiceContracts(AccountFixture):
    def submit(self, operation=None, **changes):
        kwargs = {
            "operation_id": operation or str(uuid.uuid4()),
            "channel": "fallem-prince",
            "account": "work",
            "count": 1,
            "approved_schedule": True,
            "store": self.store,
            "unit_probe": lambda _operation: False,
            **changes,
        }
        return service_jobs.submit(**kwargs)

    def test_submission_is_durable_and_idempotent_before_actor_launch(self):
        operation = str(uuid.uuid4())
        launches = []

        def launcher(_args, **_kwargs):
            record = read_private(service_jobs.jobs_root() / (operation + ".json"))
            self.assertEqual(record["state"], "accepted")
            launches.append(1)

        self.assertEqual(self.submit(operation, launcher=launcher)["state"], "accepted")
        self.assertEqual(self.submit(operation, launcher=launcher)["state"], "accepted")
        self.assertEqual(len(launches), 1)
        with self.assertRaises(ValueError):
            self.submit(operation, count=2, launcher=launcher)

    def test_concurrent_duplicate_submission_launches_exactly_one_actor(self):
        operation = str(uuid.uuid4())
        launches = []

        def submit():
            return self.submit(operation, launcher=lambda *_a, **_k: launches.append(1))

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: submit(), range(4)))
        self.assertEqual(len(launches), 1)
        self.assertTrue(all(r["state"] == "accepted" for r in results))

    def test_different_accounts_and_channels_share_one_atomic_host_admission(self):
        self.store.create("personal", "Personal")
        barrier = threading.Barrier(2)
        launches = []

        def submit(pair):
            barrier.wait()
            try:
                return self.submit(
                    account=pair[0], channel=pair[1],
                    launcher=lambda *_a, **_k: launches.append(1),
                )["state"]
            except service_jobs.CapacityReached:
                return "busy"

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, [
                ("work", "fallem-prince"), ("personal", "zaflas"),
            ]))
        self.assertCountEqual(results, ["accepted", "busy"])
        self.assertEqual(len(launches), 1)
        jobs = [p for p in service_jobs.jobs_root().glob("*.json") if p.name != "active-job.json"]
        self.assertEqual(len(jobs), 1, "busy admission creates no waiting actor or job")

    def test_capacity_requires_real_actor_and_unit_exit_and_fences_late_launch(self):
        operation = str(uuid.uuid4())
        self.submit(operation, launcher=lambda *_a, **_k: None)
        path = service_jobs.jobs_root() / (operation + ".json")
        record = read_private(path)
        record["created_at"] -= 60
        write_private(path, record)
        for state in [True, None]:
            with self.assertRaises(service_jobs.CapacityReached):
                self.submit(launcher=Mock(), unit_probe=lambda _id: state)
        next_job = self.submit(launcher=lambda *_a, **_k: None)
        service_jobs.execute(operation)
        self.assertEqual(service_jobs.status(operation)["state"], "failed")
        self.assertFalse((service_jobs.jobs_root() / (operation + ".execution")).exists())
        self.assertEqual(service_jobs.status(next_job["operation_id"])["state"], "accepted")

    def test_terminal_job_does_not_release_capacity_before_process_exit(self):
        import os

        operation = str(uuid.uuid4())
        self.submit(operation, launcher=lambda *_a, **_k: None)
        path = service_jobs.jobs_root() / (operation + ".json")
        record = read_private(path)
        record.update(state="completed", pid=os.getpid(), process_identity=service_jobs.process_identity(os.getpid()))
        write_private(path, record)
        actor = Mock()
        with self.assertRaises(service_jobs.CapacityReached):
            self.submit(launcher=actor)
        actor.assert_not_called()
        with patch.object(service_jobs, "process_identity", return_value=None):
            self.assertEqual(self.submit(launcher=lambda *_a, **_k: None)["state"], "accepted")

    def test_unit_liveness_requires_positive_systemd_evidence(self):
        import subprocess

        operation = str(uuid.uuid4())
        for output, expected in [
            ("LoadState=loaded\nActiveState=active\n", True),
            ("LoadState=loaded\nActiveState=deactivating\n", True),
            ("LoadState=not-found\nActiveState=inactive\n", False),
            ("", None),
        ]:
            with patch.object(
                service_jobs.subprocess, "run",
                return_value=subprocess.CompletedProcess([], 0, stdout=output),
            ):
                self.assertIs(service_jobs.unit_active(operation), expected)

    def test_missing_capacity_gate_during_upgrade_checks_old_admissions(self):
        operation = str(uuid.uuid4())
        self.submit(operation, launcher=lambda *_a, **_k: None)
        (service_jobs.jobs_root() / "active-job.json").unlink()
        actor = Mock()
        with self.assertRaises(service_jobs.CapacityReached):
            self.submit(launcher=actor)
        actor.assert_not_called()

    def test_unapproved_or_invalid_requests_never_launch(self):
        actor = Mock()
        for changes in [
            {"approved_schedule": False},
            {"count": 0},
            {"count": 11},
            {"account": "unknown"},
            {"operation_id": "../escape"},
        ]:
            with self.assertRaises((ValueError, SystemExit)):
                self.submit(launcher=actor, **changes)
        actor.assert_not_called()

    def test_lost_actor_remains_uncertain_and_cannot_be_replayed(self):
        operation = str(uuid.uuid4())
        self.submit(operation, launcher=lambda *_a, **_k: None)
        path = service_jobs.jobs_root() / (operation + ".json")
        record = read_private(path)
        record.update(state="running", pid=99999999, process_identity="fixture")
        write_private(path, record)
        self.assertEqual(service_jobs.status(operation)["state"], "uncertain")
        actor = Mock()
        self.assertEqual(self.submit(operation, launcher=actor)["state"], "uncertain")
        actor.assert_not_called()

    def test_channel_lock_prevents_conflicting_batches(self):
        with service_jobs.channel_lock("fallem-prince"):
            with self.assertRaises(ValueError):
                with service_jobs.channel_lock("fallem-prince"):
                    pass

    def test_actual_actor_lifecycle_is_fenced_and_requires_scheduled_evidence(self):
        from tools.ytbot import batch

        operation = str(uuid.uuid4())
        self.submit(operation, launcher=lambda *_a, **_k: None)

        def fake_batch(_count):
            run = config.RUNS / "fixture"
            run.mkdir(parents=True)
            (run / "record.json").write_text(
                json.dumps({"topic": "Fixture topic", "stages": []})
            )
            (run / "upload.json").write_text(
                json.dumps(
                    {
                        "videoId": "fixture",
                        "scheduled": True,
                        "slot": "2026-11-14 12:00",
                    }
                )
            )
            return []

        with (
            patch.object(config, "DATA", self.root / "data"),
            patch.object(batch, "run_batch", side_effect=fake_batch) as actor,
        ):
            service_jobs.execute(operation)
            service_jobs.execute(operation)
        result = service_jobs.status(operation)
        self.assertEqual(result["state"], "completed")
        self.assertEqual(result["result"]["scheduled_count"], 1)
        actor.assert_called_once()
        empty = str(uuid.uuid4())
        with patch.object(service_jobs, "process_identity", return_value=None):
            self.submit(empty, launcher=lambda *_a, **_k: None)
        with (
            patch.object(config, "DATA", self.root / "data"),
            patch.object(batch, "run_batch", return_value=[]),
        ):
            service_jobs.execute(empty)
        self.assertEqual(
            service_jobs.status(empty)["state"],
            "failed",
            "no new scheduled evidence cannot become a successful video batch",
        )

    def test_production_actor_uses_separate_bounded_systemd_unit_with_clean_env(self):
        import subprocess

        operation = str(uuid.uuid4())
        command = [
            "/private/venv/bin/python",
            "-m",
            "tools.ytbot.service",
            "_execute",
            "--operation-id",
            operation,
        ]
        environment = {
            "HOME": "/home/owner",
            "PATH": "/usr/bin:/bin",
            "DISPLAY": ":1",
            "XAUTHORITY": "/private/xauthority",
            "PYTHONPATH": str(self.root),
            "ZATURO_WORKER_TOKEN": "synthetic-worker-token",
            "OPENCODE_GO_API_KEY": "synthetic-provider-key",
        }
        with (
            patch.object(service_jobs.shutil, "which", return_value="/usr/bin/tool"),
            patch.object(
                service_jobs.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0),
            ) as run,
        ):
            service_jobs.launch_actor(command, cwd=self.root, env=environment)
        args = run.call_args_list[-1].args[0]
        for option in [
            "--unit=youtubebot-" + operation,
            "--property=MemoryHigh=12G",
            "--property=MemoryMax=16G",
            "--property=CPUQuota=200%",
            "--property=RuntimeMaxSec=12h",
            "--property=Restart=no",
            "--collect",
        ]:
            self.assertIn(option, args)
        self.assertIn("/usr/bin/env", args)
        self.assertIn("-i", args)
        self.assertIn(command[0], args)
        self.assertIn("XAUTHORITY=/private/xauthority", args)
        self.assertNotIn("synthetic-provider-key", " ".join(args))
        self.assertNotIn("synthetic-worker-token", " ".join(args))

    def test_missing_user_manager_does_not_fallback_into_worker_cgroup(self):
        with (
            patch.object(service_jobs.shutil, "which", return_value=None),
            patch.object(service_jobs.subprocess, "run") as run,
        ):
            result = self.submit()
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["error_code"], "setup_unavailable")
        run.assert_not_called()

    def test_public_result_never_contains_private_request_secrets_or_paths(self):
        operation = str(uuid.uuid4())
        self.submit(operation, launcher=lambda *_a, **_k: None)
        path = service_jobs.jobs_root() / (operation + ".json")
        record = read_private(path)
        record["secret"] = "synthetic secret"
        record["private_path"] = "/private/path"
        write_private(path, record)
        output = json.dumps(service_jobs.status(operation))
        self.assertNotIn("synthetic secret", output)
        self.assertNotIn("/private/path", output)


if __name__ == "__main__":
    unittest.main()

class GenerationAdmissionContracts(AccountFixture):
    def test_generation_requires_its_own_approval_and_keeps_publication_disabled(self):
        operation = str(uuid.uuid4())
        launched = []
        arguments = dict(operation_id=operation, channel="fallem-prince", account="work", count=4,
                         approved_schedule=False, mode="generate", store=self.store,
                         unit_probe=lambda _operation: False, launcher=lambda *_a, **_k: launched.append(1))
        with self.assertRaises(ValueError):
            service_jobs.submit(**arguments)
        first = service_jobs.submit(**arguments, approved_generate=True)
        second = service_jobs.submit(**arguments, approved_generate=True)
        self.assertEqual(first["operation_id"], second["operation_id"])
        self.assertEqual(first["mode"], "generate")
        self.assertEqual(len(launched), 1)
        stored = read_private(service_jobs.jobs_root() / (operation + ".json"))
        self.assertFalse(stored["request"]["approved_schedule"])
        self.assertTrue(stored["request"]["approved_generate"])
        with self.assertRaises(ValueError):
            service_jobs.submit(**{**arguments, "mode": "schedule", "approved_schedule": True})
