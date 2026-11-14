"""Managed, sandboxed Chrome for Testing for dedicated bot profiles only."""
from __future__ import annotations

import hashlib
import fcntl
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from . import config
from .accounts_store import private_directory, read_private, write_private

INDEX = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
VERSION = re.compile(r"\d+\.\d+\.\d+\.\d+\Z")
MAX_ARCHIVE = 400 * 1024 * 1024
MAX_EXTRACTED = 1200 * 1024 * 1024


def root() -> Path:
    return config.ROOT / ".local" / "runtime"


def managed_executable() -> Path | None:
    metadata = read_private(root() / "browser.json", {})
    version = metadata.get("version", "")
    if metadata.get("schema") != 1 or not VERSION.fullmatch(version):
        return None
    binary = root() / version / "chrome-linux64" / "chrome"
    return binary if binary.is_file() and os.access(binary, os.X_OK) else None


def executable() -> str:
    managed = managed_executable() if config.BROWSER_MODE == "managed" else None
    if config.BROWSER_MODE == "managed" and not managed:
        raise RuntimeError("run bash scripts/install-linux.sh to restore the managed browser")
    if managed:
        # Chrome cannot safely downgrade a profile created by a newer version.
        last = config.PROFILE / "Last Version"
        if last.is_file():
            previous = last.read_text().strip()
            installed = managed.parent.parent.name
            if VERSION.fullmatch(previous) and tuple(map(int, previous.split("."))) > tuple(map(int, installed.split("."))):
                raise RuntimeError("update the managed browser before opening this newer profile: bash scripts/install-linux.sh")
        return str(managed)
    system = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not system:
        raise RuntimeError("run bash scripts/install-linux.sh to prepare the bot browser")
    return system


def arguments() -> list[str]:
    result = ["--disable-background-mode"]
    if config.BROWSER_MODE == "managed":
        if not (config.EXT_PATH / "manifest.json").is_file():
            raise RuntimeError("build the Chrome extension with python3 scripts/build-chrome.py")
        result.append(f"--load-extension={config.EXT_PATH}")
    return result


def environment(*, managed: bool | None = None) -> dict[str, str]:
    env = dict(os.environ)
    if managed is None:
        managed = config.BROWSER_MODE == "managed"
    if managed:
        env.pop("CHROME_DEVEL_SANDBOX", None)
        # Ubuntu may restrict unprivileged user namespaces. Reuse only a trusted
        # package-owned SUID helper; never disable the browser sandbox.
        for candidate in [Path("/opt/google/chrome/chrome-sandbox"), Path("/usr/lib/chromium/chrome-sandbox")]:
            try:
                metadata = candidate.stat()
            except OSError:
                continue
            if metadata.st_uid == 0 and stat.S_ISREG(metadata.st_mode) and stat.S_IMODE(metadata.st_mode) == 0o4755:
                env["CHROME_DEVEL_SANDBOX"] = str(candidate)
                break
    return env


def smoke_check(binary: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="sandbox-check-", dir=root()) as profile:
        result = subprocess.run(
            [str(binary), "--headless=new", f"--user-data-dir={profile}",
             "--no-first-run", "--dump-dom", "about:blank"],
            env=environment(managed=True), capture_output=True, text=True, timeout=40,
        )
        if result.returncode or "<html>" not in result.stdout:
            raise RuntimeError(
                "browser sandbox/runtime check failed; see docs/INSTALL-LINUX.md "
                "(install the official Chrome package on Ubuntu if its sandbox is missing)"
            )


def extract_archive(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive) as package:
        members = package.infolist()
        if len(members) > 2000 or sum(item.file_size for item in members) > MAX_EXTRACTED:
            raise ValueError("browser archive exceeds extraction limits")
        # Validate the entire archive before writing anything.
        for item in members:
            name = PurePosixPath(item.filename)
            mode = item.external_attr >> 16
            if name.is_absolute() or ".." in name.parts or not name.parts or name.parts[0] != "chrome-linux64" or "\\" in item.filename or stat.S_ISLNK(mode):
                raise ValueError("unsafe browser archive member")
        for item in members:
            destination = target / item.filename
            if item.is_dir():
                destination.mkdir(mode=0o700, parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with package.open(item) as source, destination.open("xb") as output:
                shutil.copyfileobj(source, output)
            destination.chmod(0o700 if item.external_attr >> 16 & 0o111 else 0o600)


def install() -> Path:
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        raise RuntimeError("the assisted browser installer currently supports Linux x86_64 only")
    directory = private_directory(root())
    descriptor = os.open(directory / "install.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        return _install(directory)
    finally:
        os.close(descriptor)


def _install(directory: Path) -> Path:
    with urllib.request.urlopen(INDEX, timeout=60) as response:
        index = json.loads(response.read(1024 * 1024))
    version = index["channels"]["Stable"]["version"]
    if not VERSION.fullmatch(version):
        raise ValueError("invalid official browser version")
    url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/linux64/chrome-linux64.zip"
    official = index["channels"]["Stable"]["downloads"]["chrome"]
    if not any(item.get("platform") == "linux64" and item.get("url") == url for item in official):
        raise ValueError("official browser download does not match the expected Google URL")
    destination = directory / version
    binary = destination / "chrome-linux64" / "chrome"
    if not binary.is_file():
        with tempfile.TemporaryDirectory(prefix="download-", dir=directory) as temporary:
            staging = Path(temporary)
            archive = staging / "chrome.zip"
            digest = hashlib.sha256()
            total = 0
            print(f"Downloading official Chrome for Testing {version}...", flush=True)
            with urllib.request.urlopen(url, timeout=90) as response, archive.open("xb") as output:
                if response.geturl() != url:
                    raise ValueError("unexpected browser download redirect")
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_ARCHIVE:
                        raise ValueError("browser download exceeds size limit")
                    digest.update(chunk)
                    output.write(chunk)
            extracted = staging / "extracted"
            extracted.mkdir(mode=0o700)
            extract_archive(archive, extracted)
            candidate = extracted / "chrome-linux64" / "chrome"
            actual = subprocess.check_output([str(candidate), "--version"], text=True, timeout=20)
            if version not in actual:
                raise ValueError("downloaded browser version mismatch")
            write_private(extracted / "download.json", {"url": url, "sha256": digest.hexdigest()})
            extracted.rename(destination)
    smoke_check(binary)
    write_private(directory / "browser.json", {"schema": 1, "version": version})
    return binary


if __name__ == "__main__":
    try:
        print(f"Managed browser ready: {install()}")
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"Browser installation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
