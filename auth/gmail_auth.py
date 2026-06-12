import os
import re
import sys
import json
import logging
import base64
from pathlib import Path
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv(override=True)

# Suppress the file_cache deprecation warning from google-api-python-client
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]

TOKEN_FILE = Path("credentials/gmail_token.json")

# Per-Gmail-API-call timeout (seconds)
GMAIL_TIMEOUT = 15


def get_flow():
    client_id     = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise EnvironmentError("Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in .env")
    if client_id == "your_google_client_id_here" or client_secret == "your_google_client_secret_here":
        raise ValueError("Google Client ID or Client Secret has placeholder values in .env. Please configure them.")

    redirect_uri  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/gmail/callback")
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = redirect_uri
    # Use a static compliant PKCE code verifier to support stateless redirect flows
    flow.code_verifier = "static_code_verifier_for_gmail_mcp_server_flow_abcdefg123456"
    return flow


def get_auth_url():
    flow = get_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code_for_tokens(code):
    flow = get_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_data = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes) if creds.scopes else SCOPES,
        "expiry":        creds.expiry.isoformat() if creds.expiry else None,
    }
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
    print(f"Gmail tokens saved to {TOKEN_FILE}")
    return token_data


def load_credentials():
    if not TOKEN_FILE.exists():
        return None
    token_data = json.loads(TOKEN_FILE.read_text())

    from datetime import datetime
    expiry = None
    if token_data.get("expiry"):
        try:
            expiry = datetime.fromisoformat(token_data["expiry"])
        except Exception:
            pass

    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id", os.getenv("GOOGLE_CLIENT_ID")),
        client_secret=token_data.get("client_secret", os.getenv("GOOGLE_CLIENT_SECRET")),
        scopes=token_data.get("scopes", SCOPES),
        expiry=expiry,
    )
    if creds.expired and creds.refresh_token:
        print("Gmail token expired, refreshing...")
        creds.refresh(Request())
        token_data["token"] = creds.token
        token_data["expiry"] = creds.expiry.isoformat() if creds.expiry else None
        TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
        print("Gmail token refreshed")
    return creds


def get_gmail_service():
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Gmail not authenticated. Call get_auth_url() first.")
    return build("gmail", "v1", credentials=creds)


def is_authenticated():
    try:
        creds = load_credentials()
        return creds is not None and creds.valid
    except Exception:
        return False


def revoke_tokens():
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print("Gmail tokens deleted")


def normalize_gmail_query(query: str) -> str:
    """
    Normalize natural-language email search queries into Gmail search syntax.
    
    Examples:
      "from: user@x.com"  ->  "from:user@x.com"
      "from user@x.com"   ->  "from:user@x.com"
      "subject: hello"    ->  "subject:hello"
    """
    # Remove accidental spaces after colon operators (e.g. "from: x" -> "from:x")
    query = re.sub(r'\b(from|to|subject|label|in|has|filename|after|before|older_than|newer_than)\s*:\s*', r'\1:', query, flags=re.IGNORECASE)

    # Convert "from user@x.com" (no colon) to "from:user@x.com"
    # Only when there's a single word that looks like an email or name
    query = re.sub(r'\bfrom\s+([^\s:]+)', r'from:\1', query, flags=re.IGNORECASE)
    query = re.sub(r'\bto\s+([^\s:]+)', r'to:\1', query, flags=re.IGNORECASE)
    query = re.sub(r'\bsubject\s+([^\s:]+)', r'subject:\1', query, flags=re.IGNORECASE)

    return query.strip()


def _fetch_messages_metadata_batch(service, msg_ids: list) -> list:
    """Fetch metadata for multiple message IDs in a single batch request to Google API."""
    if not msg_ids:
        return []

    email_map = {}

    def callback(request_id, response, exception):
        if exception is not None:
            print(f"Error fetching metadata for message {request_id}: {exception}", file=sys.stderr)
            return

        headers = response.get("payload", {}).get("headers", [])
        email_map[request_id] = {
            "id": request_id,
            "subject": next((h["value"] for h in headers if h["name"].lower() == "subject"), "(No Subject)"),
            "from": next((h["value"] for h in headers if h["name"].lower() == "from"), "(Unknown)"),
            "to": next((h["value"] for h in headers if h["name"].lower() == "to"), ""),
            "date": next((h["value"] for h in headers if h["name"].lower() == "date"), ""),
            "snippet": response.get("snippet", ""),
            "provider": "gmail",
        }

    batch = service.new_batch_http_request(callback=callback)
    for msg_id in msg_ids:
        batch.add(
            service.users().messages().get(
                userId="me", id=msg_id, format="metadata",
                metadataHeaders=["Subject", "From", "Date", "To"]
            ),
            request_id=msg_id
        )

    try:
        batch.execute()
    except Exception as e:
        print(f"Error executing batch metadata request: {e}", file=sys.stderr)

    # Order the results to match the input msg_ids
    results = []
    for msg_id in msg_ids:
        if msg_id in email_map:
            results.append(email_map[msg_id])
    return results


def gmail_list_emails(max_results: int = 10) -> list:
    """List recent emails. Returns up to max_results emails with metadata."""
    max_results = min(max(1, max_results), 50)
    service = get_gmail_service()
    results = service.users().messages().list(userId="me", maxResults=max_results).execute()
    messages = results.get("messages", [])
    msg_ids = [m["id"] for m in messages]
    return _fetch_messages_metadata_batch(service, msg_ids)


def gmail_search_emails(query: str, max_results: int = 10) -> list:
    """Search Gmail with the given query string. Normalizes common natural-language patterns."""
    max_results = min(max(1, max_results), 50)
    normalized_query = normalize_gmail_query(query)
    service = get_gmail_service()
    results = service.users().messages().list(
        userId="me", q=normalized_query, maxResults=max_results
    ).execute()
    messages = results.get("messages", [])
    msg_ids = [m["id"] for m in messages]
    return _fetch_messages_metadata_batch(service, msg_ids)


def _get_gmail_body(payload) -> str:
    """Recursively extract the plaintext body from a Gmail message payload."""
    if "parts" in payload:
        # Prefer plain text
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        # Fall back to recursive search
        for part in payload["parts"]:
            body = _get_gmail_body(part)
            if body:
                return body
    else:
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""


def gmail_get_email(email_id: str) -> dict:
    """Fetch full email content for a specific email ID."""
    service = get_gmail_service()
    m = service.users().messages().get(userId="me", id=email_id, format="full").execute()
    headers = m.get("payload", {}).get("headers", [])
    subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "(No Subject)")
    sender  = next((h["value"] for h in headers if h["name"].lower() == "from"), "(Unknown)")
    to      = next((h["value"] for h in headers if h["name"].lower() == "to"), "")
    date    = next((h["value"] for h in headers if h["name"].lower() == "date"), "")
    body    = _get_gmail_body(m.get("payload", {}))
    return {
        "id":       email_id,
        "subject":  subject,
        "from":     sender,
        "to":       to,
        "date":     date,
        "body":     body or m.get("snippet", ""),
        "provider": "gmail",
    }


def _create_gmail_raw_message(to: str, subject: str, body: str) -> dict:
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")}


def gmail_send_email(to: str, subject: str, body: str, attachment_paths: list = None):
    service = get_gmail_service()
    if not attachment_paths:
        raw_msg = _create_gmail_raw_message(to, subject, body)
        return service.users().messages().send(userId="me", body=raw_msg).execute()

    import mimetypes
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders

    message = MIMEMultipart()
    message["to"] = to
    message["subject"] = subject
    message.attach(MIMEText(body))

    for path_str in attachment_paths:
        path = Path(path_str)
        if not path.exists():
            raise FileNotFoundError(f"Attachment file not found: {path_str}")

        content_type, encoding = mimetypes.guess_type(path_str)
        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'
        main_type, sub_type = content_type.split('/', 1)

        with open(path, 'rb') as fp:
            part = MIMEBase(main_type, sub_type)
            part.set_payload(fp.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename=path.name)
        message.attach(part)

    raw_msg = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")}
    return service.users().messages().send(userId="me", body=raw_msg).execute()


def gmail_create_draft(to: str, subject: str, body: str):
    service = get_gmail_service()
    raw_msg = _create_gmail_raw_message(to, subject, body)
    return service.users().drafts().create(userId="me", body={"message": raw_msg}).execute()


def gmail_reply_to_email(email_id: str, body: str):
    service = get_gmail_service()
    orig_msg = service.users().messages().get(userId="me", id=email_id).execute()
    thread_id = orig_msg["threadId"]
    headers = orig_msg["payload"]["headers"]
    subject    = next((h["value"] for h in headers if h["name"].lower() == "subject"), "")
    sender     = next((h["value"] for h in headers if h["name"].lower() == "from"), "")
    message_id = next((h["value"] for h in headers if h["name"].lower() == "message-id"), None)

    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject

    message = MIMEText(body)
    message["to"] = sender
    message["subject"] = subject
    if message_id:
        message["In-Reply-To"] = message_id
        message["References"] = message_id

    raw_msg = {
        "raw": base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8"),
        "threadId": thread_id,
    }
    return service.users().messages().send(userId="me", body=raw_msg).execute()


def gmail_mark_as_read(email_id: str):
    service = get_gmail_service()
    return service.users().messages().modify(
        userId="me", id=email_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def gmail_mark_as_unread(email_id: str):
    service = get_gmail_service()
    return service.users().messages().modify(
        userId="me", id=email_id, body={"addLabelIds": ["UNREAD"]}
    ).execute()


def gmail_archive_email(email_id: str):
    service = get_gmail_service()
    return service.users().messages().modify(
        userId="me", id=email_id, body={"removeLabelIds": ["INBOX"]}
    ).execute()


def gmail_delete_email(email_id: str):
    service = get_gmail_service()
    return service.users().messages().trash(userId="me", id=email_id).execute()


def gmail_forward_email(email_id: str, to: str, comment: str = ""):
    orig = gmail_get_email(email_id)
    orig_subject = orig.get("subject", "")
    orig_from = orig.get("from", "")
    orig_to = orig.get("to", "")
    orig_date = orig.get("date", "")
    orig_body = orig.get("body", "")

    subject = orig_subject if orig_subject.lower().startswith("fwd:") else f"Fwd: {orig_subject}"

    forward_header = (
        f"---------- Forwarded message ---------\n"
        f"From: {orig_from}\n"
        f"Date: {orig_date}\n"
        f"Subject: {orig_subject}\n"
        f"To: {orig_to}\n\n"
    )
    
    body = comment + "\n\n" if comment else ""
    body += forward_header + orig_body

    return gmail_send_email(to, subject, body)


def gmail_get_unread_count() -> int:
    """Return the number of unread messages in the Gmail INBOX (single lightweight API call)."""
    creds = load_credentials()
    service = build("gmail", "v1", credentials=creds)
    label = service.users().labels().get(userId="me", id="INBOX").execute()
    return label.get("messagesUnread", 0)

