"""Idempotent desktop entry and starter account; never import another profile."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from . import browser_install, config
from .accounts_store import AccountStore, write_private


def desktop_quote(value: str) -> str:
    # Desktop Exec quoting is not shell quoting. Percent is a field-code escape.
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def prepare() -> None:
    store = AccountStore()
    if not store.load()["accounts"]:
        store.create("work", "Conta de trabalho")
    applications = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    launcher = applications / "youtubebot-accounts.desktop"
    launcher.write_text(
        "[Desktop Entry]\nType=Application\nName=YoutubeBot · Contas e configuração\n"
        "Comment=Conectar Google, YouTube e ChatGPT no navegador do bot\n"
        f"Exec={desktop_quote(sys.executable)} -m tools.ytbot accounts ui\n"
        f"Path={config.ROOT}\nTerminal=false\nCategories=AudioVideo;\n",
        encoding="utf-8",
    )
    launcher.chmod(0o700)
    write_private(browser_install.root() / "install.json", {"schema": 1, "python": sys.version.split()[0], "browser_ready": bool(browser_install.managed_executable()), "extension_built": (config.EXT_PATH / "manifest.json").is_file()})
    print("Setup complete. Open YoutubeBot · Contas e configuração from the application menu.")
    print("Sign in to Google/YouTube and ChatGPT, close the browser, select your channel and verify the connection.")


if __name__ == "__main__":
    prepare()
