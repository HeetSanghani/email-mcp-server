# Email MCP Server

Connect your Gmail to Claude Desktop and talk to your inbox in plain English.

---

## What can you do with this?

After setup, just type in Claude:

> "Show me my last 10 unread emails"
> "Search for emails from my boss this week"
> "Send an email to john@gmail.com saying I'll be 10 minutes late"
> "Draft a professional reply to the job offer I got today"
> "Export all invoice emails to Excel"
> "Summarize my inbox and tell me what needs a reply"

---

## What you need before starting

| Requirement | Where to get it |
|---|---|
| Python 3.8 or newer | https://www.python.org/downloads/ |
| A Gmail account | You already have this |
| A Groq API key (free) | https://console.groq.com/keys — sign up, click "Create API Key" |
| Claude Desktop (Windows/Mac) | https://claude.ai/download |
| VS Code + Cline extension (Linux only) | https://code.visualstudio.com/ |

**Groq is completely free.** You don't need to add a credit card.

---

## Setup — Run one command

### Step 1 — Download this project

**Option A — With Git:**
```bash
git clone https://github.com/HeetSanghani/email-mcp-server.git
cd email-mcp-server
```

**Option B — Without Git (easier for beginners):**
1. Click the green **Code** button on this page
2. Click **Download ZIP**
3. Unzip the file
4. Open a terminal/command prompt **inside** the unzipped folder

---

### Step 2 — Run the setup script

```bash
python setup.py
```

On Linux/Mac if that doesn't work, try:
```bash
python3 setup.py
```

**The script guides you through everything:**
- Installs all Python packages for you automatically
- Asks for your API keys with step-by-step instructions
- Walks you through Gmail authorization (opens a browser for you)
- Configures Claude Desktop or VS Code automatically

**You never need to edit any config files manually.**

---

### Step 3 — Restart Claude Desktop

After the script finishes:

1. **Fully quit** Claude Desktop (don't just close the window — right-click the icon and Quit)
2. Reopen Claude Desktop
3. Look for the **🔨 hammer icon** at the bottom of the chat box
4. Click it — you should see the email tools listed

Now type: *"Show me my last 10 unread emails"*

---

## Running the setup script again

You can re-run `python setup.py` at any time — it detects your existing setup and shows you an update menu:

```
  [1]  Update API keys
  [2]  Re-connect Gmail
  [3]  Reinstall Python packages
  [4]  Update Claude Desktop config
  [5]  Show credential status
  [6]  Run full setup again
```

Use this if:
- You want to change your Groq key
- Your Gmail token expired
- You moved the project to a different folder
- Something stopped working after an update

---

## Gmail Setup — Detailed Guide

The setup script walks you through this, but here's the full picture:

You need to create a free "Google Cloud App" so this project can access Gmail.

1. Go to https://console.cloud.google.com (sign in with your Google account)
2. Top-left dropdown → **New Project** → give it any name → Create
3. Left menu: **APIs & Services** → **Enable APIs** → search "Gmail API" → Enable
4. Left menu: **APIs & Services** → **Credentials** → **+ CREATE CREDENTIALS** → **OAuth 2.0 Client ID**
5. If it asks about a consent screen: choose External → fill in any app name → Save & Continue
6. Application type: **Desktop app** → name it anything → **CREATE**
7. Copy the **Client ID** and **Client Secret** — paste them when the script asks

This is a one-time step. You only need to do it once per Gmail account.

---

## API Keys

| Key | Required? | Free? | Where to get it |
|---|---|---|---|
| Groq | **Yes** | **Yes, fully free** | https://console.groq.com/keys |
| Google Client ID + Secret | **Yes** | Yes (Google Cloud free tier) | Google Cloud Console (script guides you) |
| OpenAI | Optional | No (paid) | https://platform.openai.com/api-keys |
| Anthropic | Optional | No (paid) | https://console.anthropic.com |
| Gemini | Optional | Free tier | https://aistudio.google.com |

**You only need Groq + Google credentials to get started.**

---

## Available Tools

Once connected, you can ask Claude to use these tools:

| Tool | What it does |
|---|---|
| list_recent_emails | Show your recent emails from Gmail |
| search_emails | Search by sender, subject, or keyword |
| get_email_details | Read the full content of an email |
| send_email | Send a new email |
| create_draft | Save a draft without sending |
| reply_to_email | Reply to an existing thread |
| forward_email | Forward to someone else |
| mark_email_as_read / unread | Change read status |
| archive_email | Archive without deleting |
| delete_email | Move to trash |
| categorize_inbox | AI-powered inbox summary + categories |
| export_emails_to_excel | Export emails to a spreadsheet |

---

## Connecting to Claude Desktop (manual method)

The setup script does this automatically. If you need to check manually:

**Mac:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

The file should contain an entry like:
```json
{
  "mcpServers": {
    "email-mcp-server": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/email-mcp-server/run_mcp.py"]
    }
  }
}
```

The setup script fills in the correct paths for your machine automatically.

---

## Linux / Ubuntu — VS Code + Cline

Claude Desktop is not officially available on Linux. Use VS Code + Cline instead — it works the same way.

1. Install VS Code: https://code.visualstudio.com/
2. Open VS Code → Extensions panel (Ctrl+Shift+X)
3. Search "Cline" → Install
4. Click the Cline icon in the sidebar
5. Click the gear/settings icon → MCP Servers
6. Paste the contents of `cline_mcp_config_snippet.json` (created by `setup.py`)
7. Save — tools load automatically

---

## Project Structure

```
email-mcp-server/
│
├── setup.py                     ← Run this first (and re-run to update)
├── run_mcp.py                   ← MCP server entry point
├── requirements.txt             ← Python packages list
├── .env.example                 ← Template for your keys (do not edit directly)
├── .env                         ← Your actual keys (auto-created, never on GitHub)
├── .gitignore                   ← Protects your secrets from GitHub
│
├── auth/
│   ├── gmail_auth.py            ← Gmail OAuth handler
│   └── outlook_auth.py         ← Outlook OAuth handler
│
├── mcp_server/
│   └── server.py               ← All MCP tools defined here
│
├── venv/                        ← Python virtual environment (auto-created)
└── credentials/                 ← Your tokens (never pushed to GitHub)
    └── token.json               ← Auto-created after Gmail login
```

---

## FAQ

**Q: Why do I need a Groq key if Claude Desktop already has AI?**

Claude Desktop decides *which tool to call* using its own AI. But tools like `categorize_inbox` and `write_professional_reply` make their own AI calls *inside the Python server* to process your email data. That's what the Groq key is for. Groq is completely free.

**Q: Is this safe? Will my emails be shared anywhere?**

Your emails stay between your computer and Gmail's servers. Nothing is stored by this project or sent to third parties. Your `.env` and `token.json` files are local-only and listed in `.gitignore` — they are never uploaded to GitHub.

**Q: Can I use Outlook instead of Gmail?**

Outlook support is included. Run `python setup.py`, update your `.env` with the Azure app credentials, and follow the Outlook auth flow.

**Q: I moved the project folder and the tools stopped working.**

Re-run `python setup.py` and choose **option 4 — Update Claude Desktop config**. It updates the paths automatically.

**Q: The hammer icon isn't showing in Claude Desktop.**

Fully quit Claude Desktop (don't just close the window) and reopen it. If still missing, re-run `python setup.py` and choose option 4.

**Q: Do I need to leave a terminal window open?**

No. Claude Desktop starts the MCP server automatically when it needs it.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found on Windows | Reinstall Python and tick "Add to PATH" |
| `python3` not found on Mac/Linux | Install from https://www.python.org/downloads/ |
| `ModuleNotFoundError` | Re-run `python setup.py` → option 3 (Reinstall packages) |
| Hammer icon missing in Claude Desktop | Fully quit (not just close) and reopen Claude Desktop |
| Gmail auth fails | Make sure Client ID and Client Secret are correct — re-run option 2 |
| `token.json` expired / Gmail disconnected | Re-run `python setup.py` → option 2 (Re-connect Gmail) |
| OAuth redirect page shows error | This is normal — copy the `code=` value from the browser URL and paste in the terminal |
| Cline tools not loading | Check that the path in MCP config is an absolute path, not relative |
| Moved the project folder | Re-run `python setup.py` → option 4 (Update Claude Desktop config) |

---

Built with Python · Gmail API · FastMCP