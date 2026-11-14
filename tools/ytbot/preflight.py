"""Read-only, evidence-based Google/ChatGPT readiness for a requested video batch."""
from __future__ import annotations
from urllib.parse import urlsplit
from . import config

STATES = {"ready", "login_required", "unknown", "unavailable"}


def visible(page, selector):
    return page.locator(selector).first.is_visible(timeout=1000)


def inspect_page(page, service, channel_id=""):
    """Selectors establish evidence; an unknown DOM is never reported as signed in."""
    parsed = urlsplit(page.url)
    if service == "google":
        if parsed.hostname == "accounts.google.com" or visible(page, 'input[type="email"], input[type="password"]'):
            return "login_required"
        if parsed.scheme == "https" and parsed.hostname == "studio.youtube.com" and (parsed.path == "/channel/" + channel_id or parsed.path.startswith("/channel/" + channel_id + "/")) and visible(page, "ytcp-app, ytcp-shell"):
            return "ready"
    else:
        if parsed.hostname in {"auth.openai.com", "auth0.openai.com"} or visible(page, '[data-testid="login-button"], a[href*="/auth/login"], button[data-testid="signup-button"]'):
            return "login_required"
        if parsed.scheme == "https" and parsed.hostname == "chatgpt.com" and visible(page, '[data-testid="accounts-profile-button"], button[aria-label="Open profile menu"], [data-testid="profile-button"]'):
            return "ready"
    return "unknown"


def inspect_context(context, channel_id):
    checks = {}
    for service, url in [("google", "https://studio.youtube.com/channel/" + channel_id), ("chatgpt", "https://chatgpt.com/")]:
        page = context.new_page()
        try:
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            checks[service] = inspect_page(page, service, channel_id)
        except Exception:
            checks[service] = "unavailable"
        finally:
            page.close()
    return result(checks)


def result(checks):
    if set(checks) != {"google", "chatgpt"} or any(v not in STATES for v in checks.values()):
        raise ValueError("invalid readiness evidence")
    if all(value == "ready" for value in checks.values()):
        return {"ready": True, "code": "ready", "checks": checks, "summary": "Google e ChatGPT verificados no perfil dedicado. Nenhum vídeo foi criado nesta verificação."}
    missing = [name for name, value in checks.items() if value == "login_required"]
    unknown = [name for name, value in checks.items() if value in {"unknown", "unavailable"}]
    parts = []
    if missing:
        parts.append("Sua conta não está logada em " + " e ".join(missing) + ". Entre no computador de trabalho e faça login no perfil dedicado do YoutubeBot.")
    if unknown:
        parts.append("Não foi possível confirmar o acesso a " + " e ".join(unknown) + "; verifique a rede, a janela do navegador e eventuais desafios de acesso.")
    return {"ready": False, "code": "login_required" if missing else "readiness_unknown", "checks": checks, "summary": " ".join(parts) + " Nenhum vídeo foi criado ou publicado."}


def check(context):
    return inspect_context(context, config.CHANNEL_ID)
