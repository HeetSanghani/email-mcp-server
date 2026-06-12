from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from auth.gmail_auth import (
    get_auth_url as gmail_auth_url,
    exchange_code_for_tokens as gmail_exchange,
    is_authenticated as gmail_is_auth,
    revoke_tokens as gmail_revoke,
)
from auth.outlook_auth import (
    get_auth_url as outlook_auth_url,
    exchange_code_for_tokens as outlook_exchange,
    is_authenticated as outlook_is_auth,
    revoke_tokens as outlook_revoke,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def make_html_response(provider: str, status: str, detail: str = ""):
    bg_color = "#e6fffa" if status == "success" else "#fff5f5"
    border_color = "#319795" if status == "success" else "#e53e3e"
    text_color = "#2d3748"
    icon = "✓" if status == "success" else "✗"
    title = f"{provider.capitalize()} Authentication Success" if status == "success" else f"{provider.capitalize()} Authentication Failed"
    body_text = "Your account has been successfully linked. You can close this browser window and return to your application." if status == "success" else f"An error occurred during authentication: {detail}"

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: #f7fafc;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .card {{
                background-color: white;
                border-top: 5px solid {border_color};
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                text-align: center;
                max-width: 450px;
                width: 100%;
            }}
            .icon {{ font-size: 48px; color: {border_color}; margin-bottom: 20px; }}
            h1 {{ font-size: 24px; color: {text_color}; margin-bottom: 10px; }}
            p {{ color: #718096; font-size: 16px; line-height: 1.5; }}
            .badge {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                background-color: {bg_color};
                color: {border_color};
                font-weight: bold;
                font-size: 12px;
                text-transform: uppercase;
                margin-bottom: 15px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">{icon}</div>
            <span class="badge">{status}</span>
            <h1>{title}</h1>
            <p>{body_text}</p>
        </div>
    </body>
    </html>
    """)


# ── Gmail ────────────────────────────────────────────────────────────────────

@router.get("/gmail/start")
def gmail_start():
    return RedirectResponse(gmail_auth_url())


@router.get("/gmail/callback")
def gmail_callback(code: str = None, error: str = None):
    if error:
        return make_html_response("gmail", "error", error)
    if not code:
        return make_html_response("gmail", "error", "No authorization code returned.")
    try:
        gmail_exchange(code)
        return make_html_response("gmail", "success")
    except Exception as e:
        return make_html_response("gmail", "error", str(e))


@router.get("/gmail/status")
def gmail_status():
    return JSONResponse({"provider": "gmail", "connected": gmail_is_auth()})


# ✅ FIX: Accept GET, DELETE, and POST for revoke
@router.api_route("/gmail/revoke", methods=["GET", "DELETE", "POST"])
async def gmail_revoke_route(request: Request):
    gmail_revoke()
    return JSONResponse({"provider": "gmail", "connected": False, "revoked": True})


# ── Outlook ──────────────────────────────────────────────────────────────────

@router.get("/outlook/start")
def outlook_start():
    return RedirectResponse(outlook_auth_url())


@router.get("/outlook/callback")
def outlook_callback(code: str = None, error: str = None, error_description: str = None):
    if error:
        return make_html_response("outlook", "error", error_description or error)
    if not code:
        return make_html_response("outlook", "error", "No authorization code returned.")
    try:
        outlook_exchange(code)
        return make_html_response("outlook", "success")
    except Exception as e:
        return make_html_response("outlook", "error", str(e))


@router.get("/outlook/status")
def outlook_status():
    return JSONResponse({"provider": "outlook", "connected": outlook_is_auth()})


# ✅ FIX: Accept GET, DELETE, and POST for revoke
@router.api_route("/outlook/revoke", methods=["GET", "DELETE", "POST"])
async def outlook_revoke_route(request: Request):
    outlook_revoke()
    return JSONResponse({"provider": "outlook", "connected": False, "revoked": True})


# ── Combined status ──────────────────────────────────────────────────────────

@router.get("/status")
def all_status():
    return JSONResponse({
        "gmail":   {"connected": gmail_is_auth()},
        "outlook": {"connected": outlook_is_auth()},
    })