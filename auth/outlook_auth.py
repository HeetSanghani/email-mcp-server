import os
import re
import json
from pathlib import Path
from urllib.parse import quote

import msal
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

SCOPES = [
    "Mail.Read",
    "Mail.Send",
    "Mail.ReadWrite",
    "User.Read",
    "offline_access",
]

TOKEN_FILE = Path("credentials/outlook_token.json")
TENANT_ID  = os.getenv("MICROSOFT_TENANT_ID", "common")
AUTHORITY  = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Fields to select in list/search responses
MAIL_SELECT = "id,subject,from,receivedDateTime,bodyPreview,toRecipients"


def get_token_cache():
    cache = msal.SerializableTokenCache()
    if TOKEN_FILE.exists():
        try:
            cache.deserialize(TOKEN_FILE.read_text())
        except Exception:
            pass
    return cache


def save_token_cache(cache):
    if cache.has_state_changed:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(cache.serialize())


def get_msal_app(cache=None):
    client_id     = os.getenv("MICROSOFT_CLIENT_ID")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise EnvironmentError("Missing MICROSOFT_CLIENT_ID or MICROSOFT_CLIENT_SECRET in .env")
    if client_id == "your_azure_app_client_id_here" or client_secret == "your_azure_client_secret_here":
        raise ValueError("Microsoft Client ID or Client Secret has placeholder values in .env. Please configure them.")
    return msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=AUTHORITY,
        token_cache=cache,
    )


def get_auth_url():
    cache = get_token_cache()
    app = get_msal_app(cache)
    redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:8000/auth/outlook/callback")
    return app.get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )


def exchange_code_for_tokens(code):
    cache = get_token_cache()
    app = get_msal_app(cache)
    redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:8000/auth/outlook/callback")
    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    if "error" in result:
        raise RuntimeError(f"Token exchange failed: {result.get('error_description')}")
    save_token_cache(cache)
    return result


def get_access_token():
    cache = get_token_cache()
    app = get_msal_app(cache)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes=SCOPES, account=accounts[0])
        if result and "access_token" in result:
            save_token_cache(cache)
            return result["access_token"]
    raise RuntimeError("Outlook not authenticated or token expired. Call get_auth_url() first.")


def graph_request(method: str, endpoint: str, **kwargs):
    """Make an authenticated Microsoft Graph API request."""
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }
    response = requests.request(
        method, f"{GRAPH_BASE}{endpoint}",
        headers=headers, timeout=20, **kwargs
    )
    if response.status_code == 204 or not response.content:
        return {}
    if not response.ok:
        raise RuntimeError(f"Graph API error {response.status_code}: {response.text}")
    return response.json()


def is_authenticated():
    try:
        get_access_token()
        return True
    except Exception:
        return False


def revoke_tokens():
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print("Outlook tokens deleted")


def _normalize_email_result(msg: dict, provider: str = "outlook") -> dict:
    """Normalize a Graph API message object into our standard schema."""
    from_obj = msg.get("from", {}).get("emailAddress", {})
    sender_email = from_obj.get("address", "(Unknown)")
    sender_name  = from_obj.get("name", "")
    sender = f"{sender_name} <{sender_email}>" if sender_name else sender_email

    to_recipients = msg.get("toRecipients", [])
    to_address = ", ".join(
        r.get("emailAddress", {}).get("address", "") for r in to_recipients
    )

    return {
        "id":       msg["id"],
        "subject":  msg.get("subject") or "(No Subject)",
        "from":     sender,
        "to":       to_address,
        "date":     msg.get("receivedDateTime", ""),
        "snippet":  msg.get("bodyPreview", ""),
        "provider": provider,
    }


def _extract_sender_email(query: str) -> str | None:
    """
    Try to extract an email address or sender name from a search query.
    
    Handles patterns like:
      - "from:user@x.com"
      - "from: user@x.com"  
      - "from user@x.com"
    Returns the extracted address/name or None if not found.
    """
    match = re.search(
        r'\bfrom\s*:?\s*([^\s,]+)',
        query, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()
    return None


def outlook_list_emails(max_results: int = 10) -> list:
    """List recent inbox emails from Outlook."""
    max_results = min(max(1, max_results), 50)
    endpoint = f"/me/mailFolders/inbox/messages?$top={max_results}&$select={MAIL_SELECT}&$orderby=receivedDateTime desc"
    res = graph_request("GET", endpoint)
    return [_normalize_email_result(msg) for msg in res.get("value", [])]


def outlook_search_emails(query: str, max_results: int = 10) -> list:
    """
    Search Outlook emails.
    
    For sender-based searches (from:email), uses $filter for accuracy.
    For keyword searches, uses $search with proper quoting.
    
    Microsoft Graph $search and $filter cannot be combined, so we detect
    the query type and route accordingly.
    """
    max_results = min(max(1, max_results), 50)

    # Detect if this is a sender-based search
    sender_value = _extract_sender_email(query)
    
    if sender_value:
        # Use $filter for accurate sender matching (supports both email and name)
        # The 'contains' function handles partial matches for display names
        if "@" in sender_value:
            # Exact email address filter
            filter_expr = f"from/emailAddress/address eq '{sender_value}'"
        else:
            # Display name contains filter
            filter_expr = f"contains(from/emailAddress/name, '{sender_value}')"
        
        encoded_filter = quote(filter_expr)
        endpoint = (
            f"/me/messages"
            f"?$filter={encoded_filter}"
            f"&$top={max_results}"
            f"&$select={MAIL_SELECT}"
            f"&$orderby=receivedDateTime desc"
        )
    else:
        # General keyword search using $search
        # Properly quote the search term per OData spec
        search_term = query.replace("'", "''").replace('"', '\\"')
        encoded_search = quote(f'"{search_term}"')
        endpoint = (
            f"/me/messages"
            f"?$search={encoded_search}"
            f"&$top={max_results}"
            f"&$select={MAIL_SELECT}"
        )

    res = graph_request("GET", endpoint)
    return [_normalize_email_result(msg) for msg in res.get("value", [])]


def outlook_get_email(email_id: str) -> dict:
    """Fetch full email content for a specific Outlook email."""
    endpoint = f"/me/messages/{email_id}"
    msg = graph_request("GET", endpoint)
    from_obj = msg.get("from", {}).get("emailAddress", {})
    sender_email = from_obj.get("address", "(Unknown)")
    sender_name  = from_obj.get("name", "")
    sender = f"{sender_name} <{sender_email}>" if sender_name else sender_email

    to_recipients = msg.get("toRecipients", [])
    to_address = ", ".join(
        r.get("emailAddress", {}).get("address", "") for r in to_recipients
    )
    body_content = msg.get("body", {}).get("content", "")
    return {
        "id":       email_id,
        "subject":  msg.get("subject") or "(No Subject)",
        "from":     sender,
        "to":       to_address,
        "date":     msg.get("receivedDateTime", ""),
        "body":     body_content or msg.get("bodyPreview", ""),
        "provider": "outlook",
    }


def outlook_send_email(to: str, subject: str, body: str, attachment_paths: list = None):
    endpoint = "/me/sendMail"
    message = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": [{"emailAddress": {"address": to}}],
    }

    if attachment_paths:
        import mimetypes
        import base64
        attachments_list = []
        for path_str in attachment_paths:
            path = Path(path_str)
            if not path.exists():
                raise FileNotFoundError(f"Attachment file not found: {path_str}")

            content_type, _ = mimetypes.guess_type(path_str)
            if content_type is None:
                content_type = 'application/octet-stream'

            with open(path, 'rb') as fp:
                content_bytes = base64.b64encode(fp.read()).decode("utf-8")

            attachments_list.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": path.name,
                "contentType": content_type,
                "contentBytes": content_bytes
            })
        message["attachments"] = attachments_list

    payload = {"message": message}
    return graph_request("POST", endpoint, json=payload)


def outlook_create_draft(to: str, subject: str, body: str):
    endpoint = "/me/messages"
    payload = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": [{"emailAddress": {"address": to}}],
    }
    return graph_request("POST", endpoint, json=payload)


def outlook_reply_to_email(email_id: str, body: str):
    endpoint = f"/me/messages/{email_id}/reply"
    payload = {"comment": body}
    return graph_request("POST", endpoint, json=payload)


def outlook_mark_as_read(email_id: str):
    endpoint = f"/me/messages/{email_id}"
    return graph_request("PATCH", endpoint, json={"isRead": True})


def outlook_mark_as_unread(email_id: str):
    endpoint = f"/me/messages/{email_id}"
    return graph_request("PATCH", endpoint, json={"isRead": False})


def outlook_archive_email(email_id: str):
    endpoint = f"/me/messages/{email_id}/move"
    return graph_request("POST", endpoint, json={"destinationId": "archive"})


def outlook_delete_email(email_id: str):
    endpoint = f"/me/messages/{email_id}/move"
    return graph_request("POST", endpoint, json={"destinationId": "deleteditems"})


def outlook_forward_email(email_id: str, to: str, comment: str = ""):
    endpoint = f"/me/messages/{email_id}/forward"
    payload = {
        "comment": comment,
        "toRecipients": [{"emailAddress": {"address": to}}]
    }
    return graph_request("POST", endpoint, json=payload)


def outlook_get_unread_count() -> int:
    """Return the number of unread messages in the Outlook inbox (single Graph API call)."""
    try:
        result = graph_request("GET", "/me/mailFolders/inbox")
        return result.get("unreadItemCount", 0)
    except Exception:
        return 0

