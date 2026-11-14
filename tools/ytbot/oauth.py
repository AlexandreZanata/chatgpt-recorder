"""Optional read-only Google OAuth via system browser, PKCE, state and loopback callback."""

from __future__ import annotations
import base64
import hashlib
import http.server
import json
import secrets
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from .accounts_store import AccountStore, read_private, write_private

AUTHORIZATION = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
CHANNELS = "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true&maxResults=50"
SCOPES = "https://www.googleapis.com/auth/youtube.readonly"


def request_json(
    url: str, *, data: dict | None = None, access_token: str | None = None
) -> dict:
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if access_token:
        headers["Authorization"] = "Bearer " + access_token
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers)
    try:

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *_args, **_kwargs):
                return None

        with urllib.request.build_opener(NoRedirect).open(
            request, timeout=20
        ) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("OAuth response exceeds its limit")
        return json.loads(raw)
    except Exception:
        # URLs, provider error bodies and tokens are not propagated to logs/UI.
        raise ValueError(
            "Google authorization request failed; check consent, credentials and network"
        ) from None


def client_settings(path: Path) -> dict:
    info = path.lstat()
    if (
        not path.is_file()
        or path.is_symlink()
        or info.st_mode & 0o077
        or info.st_size > 65536
    ):
        raise ValueError(
            "Google desktop client file must be a private regular 0600 file"
        )
    try:
        client = json.loads(path.read_text())["installed"]
    except (ValueError, KeyError):
        raise ValueError("a Google Desktop OAuth client JSON is required") from None
    if not isinstance(client.get("client_id"), str) or not client["client_id"].endswith(
        ".apps.googleusercontent.com"
    ):
        raise ValueError("invalid Google desktop client ID")
    return {
        "client_id": client["client_id"],
        "client_secret": client.get("client_secret", ""),
    }


def connect(
    store: AccountStore,
    identifier: str,
    path: Path,
    *,
    opener=webbrowser.open,
    exchange=request_json,
) -> list[dict]:
    store.account(identifier)
    client = client_settings(path)
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    result = {}

    class Callback(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            if (
                parsed.path != "/oauth/callback"
                or len(self.path) > 8192
                or query.get("state") != [state]
                or "code" not in query
                or len(query["code"]) != 1
            ):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authorization rejected.")
                return
            result["code"] = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"Google connected. You can close this tab and return to YoutubeBot."
            )

    class Server(http.server.HTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(5)
            return connection, address

        def handle_error(self, *_args):
            pass

    server = Server(("127.0.0.1", 0), Callback)
    server.timeout = 1
    redirect = f"http://127.0.0.1:{server.server_port}/oauth/callback"
    params = {
        "client_id": client["client_id"],
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "select_account consent",
    }
    try:
        if not opener(AUTHORIZATION + "?" + urllib.parse.urlencode(params)):
            raise ValueError("could not open the system browser")
        deadline = time.monotonic() + 180
        while not result and time.monotonic() < deadline:
            server.handle_request()
        if "code" not in result:
            raise ValueError("Google sign-in timed out or was cancelled")
    finally:
        server.server_close()
    tokens = exchange(
        TOKEN,
        data={
            **client,
            "code": result["code"],
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
        },
    )
    access = tokens.get("access_token")
    if not isinstance(access, str) or len(access) > 8192:
        raise ValueError("Google did not return a valid access token")
    channels = exchange(CHANNELS, access_token=access)
    items = []
    for item in channels.get("items", [])[:50]:
        cid = item.get("id", "")
        if not isinstance(cid, str) or len(cid) != 24 or not cid.startswith("UC"):
            raise ValueError("invalid Google channel identity")
        items.append(
            {"id": cid, "title": str(item.get("snippet", {}).get("title", ""))[:200]}
        )
    if not items:
        raise ValueError(
            "the selected Google account has no accessible YouTube channel"
        )
    write_private(
        store.root / "oauth" / (identifier + ".json"),
        {
            "schema": 1,
            "tokens": tokens,
            "client": client,
            "verified_channels": items,
            "verified_at": int(time.time()),
        },
    )
    return items


def verified_channels(store: AccountStore, identifier: str) -> list[dict]:
    store.account(identifier)
    data = read_private(store.root / "oauth" / (identifier + ".json"), {})
    return data.get("verified_channels", [])
