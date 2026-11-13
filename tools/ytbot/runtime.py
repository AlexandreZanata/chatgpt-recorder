"""Hidden Xvfb Chrome runtime and profile setup for the YouTube bot."""
from __future__ import annotations
import json
import os
import shutil
import sqlite3
import subprocess
import time
import urllib.request
from pathlib import Path
from . import config
def log(message: str) -> None:
    print(f"[runtime] {message}", flush=True)
def _chrome_pids() -> list[int]:
    pids = []
    marker = f"--user-data-dir={config.PROFILE}".encode()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if b"--type=" in raw or marker not in raw.replace(b"\0", b" "):
            continue
        try:
            exe = (entry / "exe").resolve()
        except OSError:
            continue
        if exe.name == "chrome":
            pids.append(int(entry.name))
    return pids

def stop_hidden_chrome() -> None:
    for pid in _chrome_pids():
        try:
            os.kill(pid, 15)
        except OSError:
            pass
    for _ in range(60):
        if not _chrome_pids():
            break
        time.sleep(0.5)
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        (config.PROFILE / name).unlink(missing_ok=True)
    for _ in range(20):
        if not chrome_running():
            break
        time.sleep(0.5)

def chrome_running() -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{config.CDP_PORT}/json/version", timeout=2)
        return True
    except Exception:
        return False

def ensure_xvfb() -> None:
    socket = Path(f"/tmp/.X11-unix/X{config.DISPLAY.lstrip(':')}")
    if socket.exists():
        return
    subprocess.Popen(["Xvfb", config.DISPLAY, "-screen", "0", "1920x1080x24"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(20):
        time.sleep(0.5)
        if socket.exists():
            return
    raise RuntimeError("Xvfb did not start")

def _chrome_env() -> dict:
    return dict(os.environ, DISPLAY=config.DISPLAY, WAYLAND_DISPLAY="", XDG_RUNTIME_DIR="/run/user/1000")

def start_hidden_chrome() -> None:
    ensure_xvfb()
    if chrome_running():
        return
    subprocess.Popen([
        "/usr/bin/google-chrome", "--ozone-platform=x11", f"--user-data-dir={config.PROFILE}", "--profile-directory=Default",
        f"--remote-debugging-port={config.CDP_PORT}", "--no-first-run", "--no-default-browser-check",
        "--window-position=0,0", "--window-size=1600,1000",
    ], env=_chrome_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        time.sleep(1)
        if chrome_running():
            return
    raise RuntimeError("hidden Chrome did not start")

def _chrome_time() -> str:
    return str(int((time.time() + 11644473600) * 1_000_000))

def _extension_entry() -> dict:
    permissions = ["activeTab", "downloads", "storage", "tabCapture", "offscreen"]
    host = "https://chatgpt.com/*"
    return {
        "account_extension_type": 0,
        "active_permissions": {"api": permissions, "explicit_host": [host],
                               "manifest_permissions": [], "scriptable_host": [host]},
        "commands": {"_execute_action": {"suggested_key": "Ctrl+Shift+U"}},
        "content_settings": [], "creation_flags": 0, "disable_reasons": [],
        "first_install_time": _chrome_time(), "from_webstore": False,
        "granted_permissions": {"api": permissions, "explicit_host": [host],
                                "manifest_permissions": [], "scriptable_host": [host]},
        "has_started_service_worker": True, "incognito_content_settings": [],
        "incognito_preferences": {}, "last_update_time": _chrome_time(), "location": 4,
        "newAllowFileAccess": True, "path": str(config.EXT_PATH), "preferences": {},
        "regular_only_preferences": {}, "service_worker_registration_info": {"version": "0.1.0"},
        "serviceworkerevents": ["downloads.onChanged"], "was_installed_by_default": False,
        "was_installed_by_oem": False, "was_pinned_by_default": True, "withholding_permissions": False,
    }

def _copy_cookies() -> None:
    (config.PROFILE / "Default").mkdir(parents=True, exist_ok=True)
    shutil.copy2(config.MAIN_LOCAL_STATE, config.PROFILE / "Local State")
    source = sqlite3.connect(f"file:{config.MAIN_CHROME}/Cookies?mode=ro", uri=True)
    target_path = config.PROFILE / "Default" / "Cookies"
    target_path.unlink(missing_ok=True)
    target = sqlite3.connect(target_path)
    source.backup(target)
    target.close()
    source.close()

def _write_preferences() -> None:
    prefs_path = config.PROFILE / "Default" / "Preferences"
    if (config.MAIN_CHROME / "Preferences").is_file():
        shutil.copy2(config.MAIN_CHROME / "Preferences", prefs_path)
        data = json.loads(prefs_path.read_text(encoding="utf-8"))
    else:
        data = {}
    data.setdefault("extensions", {}).setdefault("ui", {})["developer_mode"] = True
    data["extensions"].setdefault("settings", {})[config.EXT_ID] = _extension_entry()
    data.setdefault("download", {})["default_directory"] = str(config.DOWNLOADS)
    data["download"]["prompt_for_download"] = False
    prefs_path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")

def setup_profile() -> None:
    if config.PROFILE == config.LEGACY_PROFILE and (config.PROFILE / "Default" / "Cookies").is_file():
        stop_hidden_chrome()
        log("using existing working profile")
        return
    if not config.EXT_PATH.is_dir():
        subprocess.run(["python3", str(config.ROOT / "scripts" / "build-chrome.py")], check=True)
    stop_hidden_chrome()
    _copy_cookies()
    _write_preferences()
    config.DOWNLOADS.mkdir(parents=True, exist_ok=True)
    log("profile configured")

def connect_hidden(playwright):
    browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{config.CDP_PORT}")
    context = browser.contexts[0]
    try:
        context.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://chatgpt.com")
    except Exception:
        log("clipboard permission not granted")
    return browser, context

def configure_downloads(browser) -> None:
    config.DOWNLOADS.mkdir(parents=True, exist_ok=True)
    session = browser.new_browser_cdp_session()
    session.send("Browser.setDownloadBehavior", {
        "behavior": "allow", "downloadPath": str(config.DOWNLOADS), "eventsEnabled": True,
    })

def configure_extension(context) -> None:
    page = context.new_page()
    try:
        page.goto(f"chrome-extension://{config.EXT_ID}/popup.html", timeout=20000)
        page.evaluate("chrome.storage.local.set({autoDownload: true, subfolder: ''})")
    except Exception:
        log("could not configure the capture extension")
    page.close()

def launch_upload_context(playwright):
    ensure_xvfb()
    last_error = None
    for attempt in range(3):
        stop_hidden_chrome()
        try:
            return playwright.chromium.launch_persistent_context(
                str(config.PROFILE), executable_path="/usr/bin/google-chrome", headless=False,
                args=["--ozone-platform=x11", "--profile-directory=Default", "--no-first-run", "--no-default-browser-check", "--window-position=0,0", "--window-size=1600,1000"],
                ignore_default_args=["--password-store=basic", "--use-mock-keychain"],
                env=_chrome_env(), accept_downloads=True,
            )
        except Exception as error:
            last_error = error
            log(f"upload browser launch failed ({attempt + 1}): {error}")
            time.sleep(2)
    raise RuntimeError(f"could not launch the upload browser: {last_error}")

def select_channel(page) -> None:
    page.wait_for_timeout(8000)
    body = page.locator("body").inner_text()
    if "Selecione um canal" in body or "Select a channel" in body or "signin_prompt" in page.url:
        link = page.get_by_text(config.CHANNEL_NAME, exact=True)
        if link.count():
            link.first.click()
            page.wait_for_timeout(6000)
        page.goto(config.STUDIO_UPLOAD, timeout=90000)
        page.wait_for_timeout(8000)
