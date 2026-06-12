import os
import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from openai import OpenAI
from anthropic import Anthropic

from mcp_server.server import (
    list_recent_emails,
    search_emails,
    get_email_details,
    send_email,
    create_draft,
    reply_to_email,
    categorize_inbox,
    export_emails_to_excel,
)

# ✅ FIX: Use correct function name — is_authenticated not is_gmail_connected
from auth.gmail_auth import is_authenticated as gmail_is_auth, gmail_get_unread_count
from auth.outlook_auth import is_authenticated as outlook_is_auth, outlook_get_unread_count

router = APIRouter(prefix="/api", tags=["chat"])


# ─── Request Schemas ──────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]


# ─── Tool Registry ────────────────────────────────────────────────────────────
funcs = {
    "list_recent_emails":      list_recent_emails,
    "search_emails":           search_emails,
    "get_email_details":       get_email_details,
    "send_email":              send_email,
    "create_draft":            create_draft,
    "reply_to_email":          reply_to_email,
    "categorize_inbox":        categorize_inbox,
    "export_emails_to_excel":  export_emails_to_excel,
}

# Tools that accept "all" as provider — skip the standard normalizer
_MULTI_PROVIDER_TOOLS = {"categorize_inbox", "export_emails_to_excel"}


# ─── Shared System Prompt ─────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are a helpful, professional Email AI Assistant. "
    "You have access to tools that list, search, read, send, draft, reply to, categorize, and export emails "
    "using the user's Gmail and Outlook accounts.\n\n"
    "Rules:\n"
    "1. When the user asks to search, find, list, or read emails, ALWAYS call the corresponding tool "
    "   to fetch fresh, real data. Never fabricate or assume email content.\n"
    "2. For sender-based searches (e.g. 'from: user@x.com'), call 'search_emails' with the "
    "   query formatted as 'from:user@x.com' (no space after the colon).\n"
    "3. When listing or searching emails, request a reasonable number of results (10–20). "
    "   Never exceed 50 unless the user explicitly asks for more.\n"
    "4. When presenting email lists, always include: sender, subject, and date.\n"
    "5. To categorize the inbox, call 'categorize_inbox' with provider='all' (or specific provider) "
    "   and ALWAYS set max_results=15 to stay within token limits. "
    "   Then summarize the counts per category clearly.\n"
    "6. To export emails to Excel, call 'export_emails_to_excel'. After success, tell the user "
    "   the filename so they can download it via the Download button shown in the chat.\n"
    "7. Be concise, professional, and clear in your responses."
)


# ─── Tools Spec ───────────────────────────────────────────────────────────────
tools_spec = [
    {
        "type": "function",
        "function": {
            "name": "list_recent_emails",
            "description": (
                "List recent emails from Gmail, Outlook, or both. "
                "Use ONLY when the user asks to see recent/latest messages without a specific search filter."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "provider": {
                        "type": ["string", "null"],
                        "enum": ["gmail", "outlook", None],
                        "description": "Email provider: 'gmail' or 'outlook'. Omit this field entirely to fetch from all connected providers."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to return. Default: 10. Max: 50."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": (
                "Search emails by sender, subject, keyword, or any combination. "
                "Use this for ANY query that filters by sender (from:), subject, date, or keywords. "
                "Format sender queries as 'from:email@address.com' (no space after colon)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Gmail-style search query. Examples: "
                            "'from:alice@example.com', 'subject:invoice', 'is:unread', "
                            "'after:2024/01/01', 'from:boss@company.com subject:urgent'"
                        )
                    },
                    "provider": {
                        "type": ["string", "null"],
                        "enum": ["gmail", "outlook", None],
                        "description": "Email provider: 'gmail' or 'outlook'. Omit this field entirely to search all connected providers."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results. Default: 10. Max: 50."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_email_details",
            "description": (
                "Get the full body and metadata of a specific email by its ID. "
                "Use this when the user wants to read the content of an email."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "The unique ID of the email to retrieve."
                    },
                    "provider": {
                        "type": "string",
                        "description": "Email provider: 'gmail' or 'outlook'."
                    }
                },
                "required": ["email_id", "provider"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send a new email using Gmail or Outlook.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to":       {"type": "string", "description": "Recipient's email address."},
                    "subject":  {"type": "string", "description": "Subject line of the email."},
                    "body":     {"type": "string", "description": "Plain text body of the email."},
                    "provider": {"type": "string", "description": "Email provider: 'gmail' or 'outlook'."}
                },
                "required": ["to", "subject", "body", "provider"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_draft",
            "description": "Create a draft email in Gmail or Outlook without sending it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to":       {"type": "string", "description": "Recipient's email address."},
                    "subject":  {"type": "string", "description": "Subject line of the email."},
                    "body":     {"type": "string", "description": "Plain text body of the email."},
                    "provider": {"type": "string", "description": "Email provider: 'gmail' or 'outlook'."}
                },
                "required": ["to", "subject", "body", "provider"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reply_to_email",
            "description": "Reply to an existing email thread. Automatically handles reply headers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {"type": "string", "description": "The unique ID of the email to reply to."},
                    "body":     {"type": "string", "description": "The reply message body."},
                    "provider": {"type": "string", "description": "Email provider: 'gmail' or 'outlook'."}
                },
                "required": ["email_id", "body", "provider"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "categorize_inbox",
            "description": (
                "Fetch emails and automatically categorize them using AI into groups: "
                "Important, Work, Newsletters, Promotions, Spam, Social, Security Alerts, Purchases/Orders. "
                "Use when the user asks to organize, categorize, sort, or group their inbox."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "Which emails to categorize: 'gmail', 'outlook', or 'all' for both accounts."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of emails to categorize. Default: 15. Max: 20."
                    }
                },
                "required": ["provider"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_emails_to_excel",
            "description": (
                "Export emails to a formatted Excel (.xlsx) file saved to ~/Downloads. "
                "Use when the user asks to export, download, save, or get emails as a spreadsheet."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "Which emails to export: 'gmail', 'outlook', or 'all' for both."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of emails to export (default: 50)."
                    },
                    "query": {
                        "type": ["string", "null"],
                        "description": "Optional search query to filter emails before exporting."
                    }
                },
                "required": ["provider"]
            }
        }
    }
]


# ─── Connection Check ─────────────────────────────────────────────────────────
def get_connection_status() -> dict:
    """Returns connection status for both providers safely."""
    gmail_ok, outlook_ok = False, False
    try:
        gmail_ok = gmail_is_auth()
    except Exception:
        pass
    try:
        outlook_ok = outlook_is_auth()
    except Exception:
        pass
    return {"gmail": gmail_ok, "outlook": outlook_ok}


def get_no_connection_message() -> str | None:
    """
    Returns a friendly message if no email account is connected.
    Returns None if at least one account is connected.
    """
    status = get_connection_status()
    if not status["gmail"] and not status["outlook"]:
        return (
            "⚠️ No email account is connected.\n\n"
            "Please connect your Gmail or Outlook account first by clicking the "
            "**Connect** button in the header or the **Manage Accounts** button in the sidebar."
        )
    return None



# ─── Provider normalizer ──────────────────────────────────────────────────────
def _normalize_provider(provider):
    """
    Normalize provider string. Groq sometimes passes 'both' or 'all' or 'any'.
    Map these to None so the tools fetch from all connected providers.
    """
    if not provider:
        return None
    p = str(provider).strip().lower()
    if p in ("both", "all", "any", "none", "null", ""):
        return None
    if p in ("gmail", "google"):
        return "gmail"
    if p in ("outlook", "microsoft", "ms"):
        return "outlook"
    return None  # unknown → fetch all


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _normalize_multi_provider(provider) -> str:
    """Normalize provider for tools that accept 'all' (categorize_inbox, export_emails_to_excel)."""
    if not provider:
        return "all"
    p = str(provider).strip().lower()
    if p in ("gmail", "google"):
        return "gmail"
    if p in ("outlook", "microsoft", "ms"):
        return "outlook"
    return "all"  # both / any / all / unknown → all


def _execute_tool(func_name: str, func_args: dict) -> str:
    func_to_call = funcs.get(func_name)
    if not func_to_call:
        return json.dumps({"error": f"Tool '{func_name}' not found."})
    try:
        if func_name in _MULTI_PROVIDER_TOOLS:
            # Normalize to "gmail" | "outlook" | "all"
            if "provider" in func_args:
                func_args["provider"] = _normalize_multi_provider(func_args["provider"])
        elif "provider" in func_args:
            # Normalize to "gmail" | "outlook" | None
            func_args["provider"] = _normalize_provider(func_args["provider"])
        result = func_to_call(**func_args)
        # Strip base64_xlsx — it's huge and useless for the LLM; file is saved locally
        if func_name == "export_emails_to_excel" and isinstance(result, dict):
            result = {k: v for k, v in result.items() if k != "base64_xlsx"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Tool execution error: {str(e)}"})



# ─── OpenAI-Compatible Handler (Groq, Gemini, OpenAI) ────────────────────────
def handle_openai_compatible_chat(
    api_messages: List[Dict],
    api_key: str,
    base_url: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url)

    kwargs = {}
    if base_url and "groq.com" in base_url:
        kwargs["parallel_tool_calls"] = False

    for iteration in range(8):
        response = client.chat.completions.create(
            model=model,
            messages=api_messages,
            tools=tools_spec,
            tool_choice="auto",
            **kwargs
        )

        response_message = response.choices[0].message

        if not response_message.tool_calls:
            return response_message.content or ""

        msg_dict: Dict = {
            "role":    "assistant",
            "content": response_message.content or "",
            "tool_calls": [
                {
                    "id":   tc.id,
                    "type": tc.type,
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response_message.tool_calls
            ],
        }
        api_messages.append(msg_dict)

        for tool_call in response_message.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                func_args = {}

            result_str = _execute_tool(func_name, func_args)
            api_messages.append({
                "role":         "tool",
                "tool_call_id": tool_call.id,
                "name":         func_name,
                "content":      result_str,
            })

    final_response = client.chat.completions.create(
        model=model,
        messages=api_messages,
        tools=tools_spec,
        tool_choice="none",
        **kwargs
    )
    return final_response.choices[0].message.content or "I was unable to complete the request."


# ─── Anthropic Handler ────────────────────────────────────────────────────────
def handle_anthropic_chat(req_messages: List[ChatMessage], anthropic_key: str) -> str:
    client = Anthropic(api_key=anthropic_key)

    anthropic_tools = [
        {
            "name":         tool["function"]["name"],
            "description":  tool["function"]["description"],
            "input_schema": tool["function"]["parameters"],
        }
        for tool in tools_spec
    ]

    messages = [
        {"role": m.role, "content": m.content}
        for m in req_messages
        if m.role != "system"
    ]

    for _ in range(8):
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=anthropic_tools,
        )

        if response.stop_reason != "tool_use":
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            return "\n".join(text_blocks) if text_blocks else ""

        assistant_content = []
        tool_calls_to_run = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type":  "tool_use",
                    "id":    block.id,
                    "name":  block.name,
                    "input": block.input,
                })
                tool_calls_to_run.append(block)

        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for tool_call in tool_calls_to_run:
            result_str = _execute_tool(tool_call.name, tool_call.input)
            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": tool_call.id,
                "content":     result_str,
            })

        messages.append({"role": "user", "content": tool_results})

    return "I was unable to complete the request within the allowed steps."


# ─── Chat Endpoint ────────────────────────────────────────────────────────────
@router.post("/chat")
def chat_with_agent(req: ChatRequest):

    # ✅ FIX: Guard — check connection BEFORE hitting AI
    no_conn_msg = get_no_connection_message()
    if no_conn_msg:
        return {"response": no_conn_msg}

    provider = os.getenv("AI_PROVIDER", "openai").strip().lower()

    try:
        if provider == "anthropic":
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_key or anthropic_key == "your_anthropic_key_here":
                return JSONResponse(status_code=400, content={"error": "Anthropic API Key is not configured."})
            reply_text = handle_anthropic_chat(req.messages, anthropic_key)
            return {"response": reply_text}

        elif provider == "gemini":
            gemini_key = os.getenv("GEMINI_API_KEY")
            if not gemini_key or gemini_key == "your_gemini_key_here":
                return JSONResponse(status_code=400, content={"error": "Gemini API Key is not configured."})
            api_messages = [{"role": m.role, "content": m.content} for m in req.messages if m.role != "system"]
            api_messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
            reply_text = handle_openai_compatible_chat(
                api_messages=api_messages,
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                model="gemini-2.0-flash",
            )
            return {"response": reply_text}

        elif provider == "groq":
            groq_key = os.getenv("GROQ_API_KEY")
            if not groq_key or groq_key == "your_groq_key_here":
                return JSONResponse(status_code=400, content={"error": "Groq API Key is not configured."})
            api_messages = [{"role": m.role, "content": m.content} for m in req.messages if m.role != "system"]
            api_messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
            reply_text = handle_openai_compatible_chat(
                api_messages=api_messages,
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1",
                model="llama-3.3-70b-versatile",
            )
            return {"response": reply_text}

        else:
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key or openai_key == "your_openai_api_key_here":
                return JSONResponse(status_code=400, content={"error": "OpenAI API Key is not configured."})
            api_messages = [{"role": m.role, "content": m.content} for m in req.messages if m.role != "system"]
            api_messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
            reply_text = handle_openai_compatible_chat(
                api_messages=api_messages,
                api_key=openai_key,
            )
            return {"response": reply_text}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error calling {provider.capitalize()} API: {str(e)}"}
        )


# ─── Connection status endpoint (used by frontend polling) ────────────────────
@router.get("/connection-status")
def connection_status():
    """Real-time connection status for frontend polling after disconnect."""
    status = get_connection_status()
    return JSONResponse(status)


# ─── Excel download endpoint ──────────────────────────────────────────────────
from pathlib import Path as _Path
from fastapi.responses import FileResponse as _FileResponse

@router.get("/download-excel")
def download_excel(filename: str):
    """Serve an exported Excel file. Only ~/Downloads is accessible (path-traversal safe)."""
    downloads = _Path.home() / "Downloads"
    file_path = (downloads / filename).resolve()
    if not str(file_path).startswith(str(downloads.resolve())):
        return JSONResponse(status_code=403, content={"error": "Access denied."})
    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": f"File '{filename}' not found."})
    return _FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


# ─── Unread count endpoint (polled by frontend every 5 min for notification badge) ───────
@router.get("/unread-count")
def unread_count():
    """Return unread email counts for Gmail and Outlook without going through the LLM."""
    counts = {"gmail": 0, "outlook": 0, "total": 0}
    if gmail_is_auth():
        try:
            counts["gmail"] = gmail_get_unread_count()
        except Exception:
            pass
    if outlook_is_auth():
        try:
            counts["outlook"] = outlook_get_unread_count()
        except Exception:
            pass
    counts["total"] = counts["gmail"] + counts["outlook"]
    return JSONResponse(counts)