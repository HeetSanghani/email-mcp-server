#!/usr/bin/env python3
"""
Email MCP Server — Master Setup Script
=======================================
Run this ONCE to install everything and configure your credentials.
Re-run anytime to update a key or fix something.

  python setup.py
"""

import os
import sys
import json
import getpass
import platform
import subprocess
import shutil
from pathlib import Path

# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def clear():
    os.system("cls" if platform.system() == "Windows" else "clear")


def banner(title, subtitle=""):
    width = 60
    print("\n" + "═" * width)
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print("═" * width)


def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def ok(msg):   print(f"  ✓  {msg}")
def warn(msg): print(f"  ⚠  {msg}")
def err(msg):  print(f"  ✗  {msg}")
def info(msg): print(f"     {msg}")
def tip(msg):  print(f"  💡 {msg}")
def step(n, total, msg): print(f"\n  [{n}/{total}] {msg}")


def pause(msg="Press ENTER to continue"):
    try:
        input(f"\n  ➜  {msg} ... ")
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Setup cancelled. Run again when ready.\n")
        sys.exit(0)


def ask(prompt, default=""):
    suffix = f" (default: {default})" if default else ""
    try:
        val = input(f"\n  ➜  {prompt}{suffix}\n     Your answer: ").strip()
        return val if val else default
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Setup cancelled. Run again when ready.\n")
        sys.exit(0)


def ask_secret(prompt, hint=""):
    if hint:
        print(f"\n  ➜  {prompt}")
        print(f"     (currently saved: {hint})")
        print("     Type a new value to replace it, or press ENTER to keep it.")
    else:
        print(f"\n  ➜  {prompt}")
        print("     (nothing will be shown as you type — that is normal)")
    try:
        val = getpass.getpass("     Your answer: ").strip()
        return val
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Setup cancelled. Run again when ready.\n")
        sys.exit(0)


def ask_yn(prompt, default="y"):
    options = " [Y/n]" if default == "y" else " [y/N]"
    try:
        val = input(f"\n  ➜  {prompt}{options}: ").strip().lower()
        if val == "":
            return default == "y"
        return val in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Setup cancelled. Run again when ready.\n")
        sys.exit(0)


def masked(val):
    if not val or val.startswith("your_") or val == "":
        return "not set yet"
    if len(val) <= 8:
        return "****"
    return val[:4] + "·····" + val[-4:]


# ─────────────────────────────────────────────────────────────
#  .env helpers
# ─────────────────────────────────────────────────────────────

def load_env(path=".env"):
    env = {}
    p = Path(path)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env


def save_env(env, path=".env"):
    example = Path(".env.example")
    lines = []
    written = set()
    if example.exists():
        for line in example.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                lines.append(line)
            elif "=" in s:
                k = s.split("=", 1)[0].strip()
                lines.append(f"{k}={env.get(k, '')}")
                written.add(k)
    for k, v in env.items():
        if k not in written:
            lines.append(f"{k}={v}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
#  Step 0 — Python version check
# ─────────────────────────────────────────────────────────────

def check_python():
    if sys.version_info < (3, 8):
        err(f"Python 3.8 or newer is required.")
        info(f"You have: Python {sys.version}")
        info("Download the latest Python from: https://www.python.org/downloads/")
        sys.exit(1)
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


# ─────────────────────────────────────────────────────────────
#  Step 1 — Virtual environment + dependencies
# ─────────────────────────────────────────────────────────────

def setup_venv_and_deps():
    section("STEP 1 of 5 — Installing Python dependencies")

    info("This installs all the Python libraries the project needs.")
    info("It only takes about 30–60 seconds.")
    print()

    venv_dir = Path("venv")

    # Create venv if it doesn't exist
    if not venv_dir.exists():
        print("  Creating a virtual environment (isolated Python sandbox)...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", "venv"],
                check=True, capture_output=True
            )
            ok("Virtual environment created (venv/)")
        except subprocess.CalledProcessError as e:
            err("Could not create virtual environment.")
            info("Try running:  python3 -m venv venv")
            info(e.stderr.decode()[:300] if e.stderr else "")
            sys.exit(1)
    else:
        ok("Virtual environment already exists (venv/)")

    # Pick the right python inside the venv
    system = platform.system().lower()
    if "windows" in system:
        venv_python = Path("venv") / "Scripts" / "python.exe"
        venv_pip    = Path("venv") / "Scripts" / "pip.exe"
    else:
        venv_python = Path("venv") / "bin" / "python"
        venv_pip    = Path("venv") / "bin" / "pip"

    if not venv_python.exists():
        err("Virtual environment looks broken. Delete the venv/ folder and re-run.")
        sys.exit(1)

    req = Path("requirements.txt")
    if not req.exists():
        warn("requirements.txt not found — skipping dependency install.")
        return venv_python

    print("  Installing packages from requirements.txt ...")
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err("Dependency install failed. Error details:")
        print(result.stderr[:600] if result.stderr else "(no details)")
        info("Try running this command yourself:")
        info(f"  {venv_python} -m pip install -r requirements.txt")
        sys.exit(1)

    ok("All packages installed successfully")
    return venv_python


# ─────────────────────────────────────────────────────────────
#  Step 2 — credentials/ folder + .gitignore
# ─────────────────────────────────────────────────────────────

def setup_folders():
    section("STEP 2 of 5 — Setting up folder structure")

    creds = Path("credentials")
    creds.mkdir(exist_ok=True)
    (creds / ".gitkeep").touch()

    readme = creds / "README.txt"
    if not readme.exists():
        readme.write_text(
            "This folder holds your OAuth tokens.\n"
            "These files are in .gitignore — they are NEVER uploaded to GitHub.\n\n"
            "  token.json           ← Created automatically after Gmail login\n"
            "  outlook_token.json   ← Created automatically after Outlook login\n"
        )
    ok("credentials/ folder ready")

    # .gitignore
    gitignore = Path(".gitignore")
    needed = [".env", "credentials/", "token.json", "venv/", "__pycache__/", "*.pyc"]
    existing_text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    missing = [e for e in needed if e not in existing_text]
    if missing:
        with open(gitignore, "a", encoding="utf-8") as f:
            f.write("\n# Added by setup.py — do not remove\n")
            for e in missing:
                f.write(f"{e}\n")
        ok(f".gitignore updated — secrets protected from GitHub")
    else:
        ok(".gitignore already covers all secrets")


# ─────────────────────────────────────────────────────────────
#  Step 3 — API keys (.env)
# ─────────────────────────────────────────────────────────────

def setup_api_keys(update_only=False):
    section("STEP 3 of 5 — API Keys")

    env = load_env(".env")
    # Merge defaults from .env.example
    for k, v in load_env(".env.example").items():
        if k not in env:
            env[k] = v

    # ── Groq ──────────────────────────────────────────────
    print("""
  ┌─────────────────────────────────────────────────────┐
  │  GROQ API KEY  (required — but FREE)                │
  └─────────────────────────────────────────────────────┘

  Groq runs AI models for free. The project uses it for
  smart features like "categorize my inbox" and 
  "write a professional reply".

  How to get your free Groq key (takes 2 minutes):
    1. Open this link:  https://console.groq.com/keys
    2. Sign up or log in (Google login works)
    3. Click "Create API Key"
    4. Copy the key that starts with  gsk_...
    5. Paste it below
""")
    curr = env.get("GROQ_API_KEY", "")
    val = ask_secret("Paste your Groq API key here", masked(curr))
    if val:
        env["GROQ_API_KEY"] = val
    elif curr and not curr.startswith("your_"):
        ok(f"Keeping existing Groq key ({masked(curr)})")
    else:
        warn("No Groq key saved — some features won't work until you add one")

    # ── Optional keys ─────────────────────────────────────
    print("""
  ┌─────────────────────────────────────────────────────┐
  │  OPTIONAL API KEYS                                   │
  └─────────────────────────────────────────────────────┘

  These are optional. You only need one of the above (Groq).
  Press ENTER to skip any you don't have.
""")
    optional = {
        "OPENAI_API_KEY":    ("OpenAI key (sk-...)",    "https://platform.openai.com/api-keys"),
        "ANTHROPIC_API_KEY": ("Anthropic key (sk-ant-...)", "https://console.anthropic.com"),
        "GEMINI_API_KEY":    ("Gemini key",             "https://aistudio.google.com"),
    }
    for k, (label, url) in optional.items():
        curr = env.get(k, "")
        if curr and not curr.startswith("your_"):
            if not ask_yn(f"  {label} is saved ({masked(curr)}). Update it?", default="n"):
                continue
        print(f"     Get it here: {url}")
        val = ask_secret(f"{label}", masked(curr) if curr and not curr.startswith("your_") else "")
        if val:
            env[k] = val

    # ── AI Provider choice ────────────────────────────────
    print("""
  ┌─────────────────────────────────────────────────────┐
  │  Which AI provider should the server use?           │
  └─────────────────────────────────────────────────────┘
  This is the AI that powers "categorize inbox", 
  "write reply" and similar smart features.
""")
    providers = ["Groq (free, recommended)", "OpenAI", "Anthropic", "Gemini"]
    provider_keys = ["Groq", "OpenAI", "Anthropic", "Gemini"]
    curr_prov = env.get("AI_PROVIDER", "Groq")
    for i, p in enumerate(providers, 1):
        marker = " ← current" if provider_keys[i-1] == curr_prov else ""
        info(f"[{i}] {p}{marker}")
    choice = ask("Enter 1, 2, 3, or 4 (press ENTER to keep current)", "")
    if choice in ("1", "2", "3", "4"):
        env["AI_PROVIDER"] = provider_keys[int(choice) - 1]
        ok(f"AI provider set to: {env['AI_PROVIDER']}")

    save_env(env)
    ok(".env file saved (protected — only you can read it)")


# ─────────────────────────────────────────────────────────────
#  Step 4 — Gmail OAuth
# ─────────────────────────────────────────────────────────────

def setup_gmail(venv_python):
    section("STEP 4 of 5 — Gmail Connection")

    token = Path("credentials/token.json")
    if token.exists():
        ok("Gmail already connected (token.json found)")
        if not ask_yn("Connect a different Gmail account?", default="n"):
            return

    env = load_env(".env")

    # ── Part A: Google Cloud credentials ──────────────────
    client_id     = env.get("GOOGLE_CLIENT_ID", "")
    client_secret = env.get("GOOGLE_CLIENT_SECRET", "")

    has_creds = (
        client_id and not client_id.startswith("your_") and
        client_secret and not client_secret.startswith("your_")
    )

    if not has_creds:
        print("""
  ┌─────────────────────────────────────────────────────┐
  │  GMAIL SETUP — Part A: Google Cloud credentials     │
  └─────────────────────────────────────────────────────┘

  You need to create a free "Google Cloud App" so this
  project can access your Gmail. Follow these steps:

  ① Go to:  https://console.cloud.google.com
     (Sign in with the same Google account as your Gmail)

  ② Top-left dropdown → "New Project"
     Give it any name (e.g. "Email MCP") → click Create

  ③ In the left menu: "APIs & Services" → "Enable APIs"
     Search for "Gmail API" → click it → click ENABLE

  ④ Left menu: "APIs & Services" → "Credentials"
     Click "+ CREATE CREDENTIALS" → "OAuth 2.0 Client ID"
     If asked about consent screen: External → fill in app name → Save

  ⑤ Application type: Desktop app
     Name: anything (e.g. "Email MCP Client") → CREATE

  ⑥ A popup shows your Client ID and Client Secret
     Copy both — you'll paste them below
""")
        pause("Press ENTER when you have your Client ID and Client Secret ready")

    print()
    curr_id = client_id if client_id and not client_id.startswith("your_") else ""
    if curr_id:
        print(f"  Current Client ID: {masked(curr_id)}")
        if ask_yn("  Keep the existing Client ID?", default="y"):
            pass
        else:
            curr_id = ""

    if not curr_id:
        print("  Paste your Google Client ID below.")
        print("  It looks like:  123456789-abcdefg.apps.googleusercontent.com")
        new_id = ask("Client ID")
        if new_id:
            env["GOOGLE_CLIENT_ID"] = new_id

    curr_secret = client_secret if client_secret and not client_secret.startswith("your_") else ""
    val = ask_secret(
        "Paste your Google Client Secret",
        masked(curr_secret) if curr_secret else ""
    )
    if val:
        env["GOOGLE_CLIENT_SECRET"] = val

    if not env.get("GOOGLE_REDIRECT_URI") or env.get("GOOGLE_REDIRECT_URI","").startswith("your_"):
        env["GOOGLE_REDIRECT_URI"] = "http://localhost:8000/auth/gmail/callback"

    save_env(env)
    ok("Gmail credentials saved to .env")

    # ── Part B: Run OAuth ──────────────────────────────────
    print("""
  ┌─────────────────────────────────────────────────────┐
  │  GMAIL SETUP — Part B: Authorize access             │
  └─────────────────────────────────────────────────────┘

  Now we'll open your browser so you can log in to Gmail
  and give this project permission to access your inbox.

  What will happen:
    → A browser window will open automatically
    → Log in with your Gmail account
    → Click "Allow" or "Continue"
    → The browser may show a "redirect" page — that's OK
    → Come back here when it's done
""")
    pause("Press ENTER to open the browser for Gmail login")

    auth_script = None
    for candidate in ["auth/gmail_auth.py", "gmail_auth.py"]:
        if Path(candidate).exists():
            auth_script = candidate
            break

    if not auth_script:
        warn("auth/gmail_auth.py not found.")
        info("Run it manually later: python auth/gmail_auth.py")
        return

    result = subprocess.run([str(venv_python), auth_script])

    if result.returncode != 0:
        err("Gmail authentication failed.")
        info("Common fixes:")
        info("  • Make sure Client ID and Secret are correct")
        info("  • Make sure Gmail API is enabled in Google Cloud Console")
        info("  • Try running manually: python auth/gmail_auth.py")
        return

    if Path("credentials/token.json").exists() or Path("token.json").exists():
        ok("Gmail connected successfully! token.json saved.")
    else:
        warn("token.json not found after auth — try running auth/gmail_auth.py manually")


# ─────────────────────────────────────────────────────────────
#  Step 5 — Claude Desktop / VS Code config
# ─────────────────────────────────────────────────────────────

def setup_desktop_config(venv_python):
    section("STEP 5 of 5 — Connecting to Claude Desktop")

    root       = Path(__file__).parent.absolute()
    run_mcp    = root / "run_mcp.py"
    system     = platform.system().lower()
    py_path    = str(Path(venv_python).absolute())

    mcp_entry = {
        "command":     py_path,
        "args":        [str(run_mcp)],
        "env":         {},
        "disabled":    False,
        "alwaysAllow": []
    }
    mcp_config = {"mcpServers": {"email-mcp-server": mcp_entry}}

    # ── Linux path ────────────────────────────────────────
    if "linux" in system:
        snippet = root / "cline_mcp_config_snippet.json"
        snippet.write_text(json.dumps(mcp_config, indent=2))
        print(f"""
  Linux detected — Claude Desktop is not available on Linux.
  Use VS Code + Cline instead (it works the same way).

  How to connect:
    ① Install VS Code:  https://code.visualstudio.com/
    ② Open VS Code → Extensions (Ctrl+Shift+X)
    ③ Search "Cline" → Install
    ④ Click the Cline icon in the sidebar
    ⑤ Click the gear/settings icon → "MCP Servers"
    ⑥ Paste the contents of this file:
         {snippet}

  The config has been saved for you at:
    {snippet}
""")
        ok("Config snippet saved for VS Code/Cline")
        return

    # ── Windows / Mac ─────────────────────────────────────
    if "darwin" in system:
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif "windows" in system:
        appdata = os.environ.get("APPDATA", str(Path.home()))
        config_path = Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:
        config_path = None

    # Save a backup snippet regardless
    snippet = root / "claude_desktop_config_snippet.json"
    snippet.write_text(json.dumps(mcp_config, indent=2))
    ok(f"Config snippet saved: claude_desktop_config_snippet.json")

    if config_path and config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

        already = "email-mcp-server" in existing.get("mcpServers", {})
        if already:
            ok("email-mcp-server already in Claude Desktop config")
            if not ask_yn("Update the paths (needed if you moved the project folder)?", default="n"):
                return

        existing.setdefault("mcpServers", {})["email-mcp-server"] = mcp_entry
        try:
            config_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            ok(f"Claude Desktop config updated")
            info(f"File: {config_path}")
        except PermissionError:
            err("Permission denied writing to Claude Desktop config.")
            info(f"Add the snippet manually from: {snippet}")

    elif config_path:
        print(f"""
  Claude Desktop config file not found at:
    {config_path}

  This usually means Claude Desktop hasn't been opened yet.

  How to fix:
    ① Download Claude Desktop: https://claude.ai/download
    ② Install and open it once (even just to the main screen)
    ③ Come back here and re-run:  python setup.py
       Choose "Update Claude Desktop config" from the menu

  The config snippet has been saved at:
    {snippet}
""")
        warn("Claude Desktop not found — snippet saved for later")


# ─────────────────────────────────────────────────────────────
#  Full first-time setup
# ─────────────────────────────────────────────────────────────

def full_setup():
    clear()
    banner(
        "Email MCP Server — Setup",
        "Connect your Gmail to Claude in ~5 minutes"
    )
    print("""
  This script will:
    ✓  Install all Python packages automatically
    ✓  Save your API keys securely
    ✓  Walk you through Gmail authorization step by step
    ✓  Configure Claude Desktop automatically

  You can press Ctrl+C at any time to cancel.
  Run this script again if anything goes wrong — it is safe to re-run.
""")
    check_python()

    venv_python = setup_venv_and_deps()
    setup_folders()
    setup_api_keys()
    setup_gmail(venv_python)
    setup_desktop_config(venv_python)

    system = platform.system().lower()
    clear()
    banner("Setup Complete!", "Everything is installed and configured.")
    print("""
  What was set up:
    ✓  Python packages installed (venv/)
    ✓  API keys saved (.env — private, not on GitHub)
    ✓  credentials/ folder ready
    ✓  Gmail authorization done
    ✓  Claude Desktop config updated
""")
    if "linux" in system:
        print("""  Next steps (Linux):
    ① Open VS Code + Cline extension
    ② Paste the config from:  cline_mcp_config_snippet.json
    ③ Reload Cline — tools will appear
    ④ Try typing:  "Show me my last 10 emails"
""")
    else:
        print("""  Next steps:
    ① Fully quit Claude Desktop (don't just close the window)
    ② Reopen Claude Desktop
    ③ Look for the 🔨 hammer icon at the bottom of the chat box
    ④ Click it — you should see the email tools listed
    ⑤ Try typing:  "Show me my last 10 unread emails"
""")
    print("""  If something isn't working:
    ① Re-run this script:   python setup.py
    ② Choose the option that matches your problem
    ③ Check the README.md for troubleshooting tips
""")


# ─────────────────────────────────────────────────────────────
#  Update menu (shown when already configured)
# ─────────────────────────────────────────────────────────────

def update_menu(venv_python):
    system = platform.system().lower()
    while True:
        clear()
        banner(
            "Email MCP Server — Update Menu",
            "Your setup is already working. What do you want to update?"
        )
        print("""
  [1]  Update API keys          (change Groq, OpenAI, etc.)
  [2]  Re-connect Gmail          (new account or token expired)
  [3]  Reinstall Python packages (if you get import errors)
  [4]  Update Claude Desktop config  (if you moved the project)
  [5]  Show credential status    (masked — safe to share)
  [6]  Run full setup again
  [0]  Exit
""")
        choice = ask("Enter a number", "0")

        if choice == "1":
            setup_api_keys(update_only=True)
            pause("Done. Press ENTER to go back to the menu")
        elif choice == "2":
            setup_gmail(venv_python)
            pause("Done. Press ENTER to go back to the menu")
        elif choice == "3":
            section("Reinstalling packages")
            result = subprocess.run(
                [str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"],
                capture_output=False
            )
            if result.returncode == 0:
                ok("All packages reinstalled")
            else:
                err("Reinstall failed — see errors above")
            pause("Press ENTER to go back to the menu")
        elif choice == "4":
            setup_desktop_config(venv_python)
            pause("Done. Press ENTER to go back to the menu")
        elif choice == "5":
            show_status()
            pause("Press ENTER to go back to the menu")
        elif choice == "6":
            full_setup()
            return
        elif choice == "0":
            print("\n  Bye!\n")
            sys.exit(0)
        else:
            warn("Invalid choice — please enter a number from the menu")


def show_status():
    section("Credential Status")
    env = load_env(".env")
    keys = [
        ("GROQ_API_KEY",       "Groq API key"),
        ("OPENAI_API_KEY",     "OpenAI key"),
        ("ANTHROPIC_API_KEY",  "Anthropic key"),
        ("GEMINI_API_KEY",     "Gemini key"),
        ("GOOGLE_CLIENT_ID",   "Google Client ID"),
        ("GOOGLE_CLIENT_SECRET","Google Client Secret"),
        ("AI_PROVIDER",        "AI Provider"),
    ]
    for k, label in keys:
        v = env.get(k, "")
        if k == "AI_PROVIDER":
            display = v if v else "not set"
        else:
            display = masked(v)
        status = "✓" if v and not v.startswith("your_") else "✗"
        print(f"  {status}  {label:<26} {display}")

    print()
    token_ok = Path("credentials/token.json").exists() or Path("token.json").exists()
    print(f"  {'✓' if token_ok else '✗'}  Gmail token                  {'found' if token_ok else 'not found — run step 4'}")

    venv_ok = Path("venv").exists()
    print(f"  {'✓' if venv_ok else '✗'}  Virtual environment           {'found (venv/)' if venv_ok else 'missing — run step 1'}")


# ─────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────

def already_configured():
    return (
        Path(".env").exists() and
        (Path("credentials/token.json").exists() or Path("token.json").exists())
    )


def get_venv_python():
    system = platform.system().lower()
    if "windows" in system:
        p = Path("venv") / "Scripts" / "python.exe"
    else:
        p = Path("venv") / "bin" / "python"
    return p if p.exists() else Path(sys.executable)


def main():
    check_python()

    if already_configured():
        clear()
        banner(
            "Email MCP Server — Setup",
            "Existing setup detected"
        )
        print("""
  Your setup is already configured.
  (.env and token.json both found)
""")
        venv_python = get_venv_python()
        if ask_yn("Open the update menu to change something?", default="y"):
            update_menu(venv_python)
        else:
            print("\n  Nothing changed. Run again anytime.\n")
    else:
        full_setup()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Setup cancelled. Run again when ready.\n")
        sys.exit(0)