# 🚀 How to Run & Use the Email Assistant (Running Guide)

This guide shows you the **3 different ways** you can launch and interact with your Email Assistant. Depending on how you want to work, choose the method that fits best!

---

## 🗺️ Quick Summary of the 3 Methods

| Method | What is it? | Great for... | Cost |
| :--- | :--- | :--- | :--- |
| **1. VS Code + Cline** | Directly inside your code editor. | Writing code, replying to job alerts, automating files. | **100% Free** (using OpenRouter free tier) |
| **2. Custom Web UI** | A beautiful, clean chat screen in your web browser. | Normal conversation, dark-mode styling, voice typing. | **Free / Paid** (based on `.env` keys) |
| **3. MCP Inspector** | A diagnostic testing page for developers. | Troubleshooting tools, inspecting raw API data. | **100% Free** (strictly local testing) |

---

## 1️⃣ Method 1: Using VS Code + Cline (Editor Integration)
This lets the AI read your emails and act as your coding/job assistant directly inside VS Code.

### How it runs:
When you configure Cline, **VS Code starts the python server automatically in the background**. You do not need to run any commands in your terminal to keep it running!

### Steps to use:
1. Open your Cline chat panel in VS Code.
2. Ensure the model is set to `google/gemma-4-31b-it:free` (so it costs nothing).
3. Type your instructions in natural English (e.g., *"Summarize my last 3 emails"*).
4. Cline will automatically call the tools, fetch your emails, and respond.

---

## 2️⃣ Method 2: Using the Custom Web UI (Browser Chat)
We built a beautiful, dedicated chat website for you to interact with your assistant. It includes features like:
- **Theme Toggle:** Switch between a sleek Light and Dark mode.
- **Voice Typing:** Speak to your email assistant hands-free.
- **Unread Badges:** Keeps track of how many unread emails are in your inbox.

### How to run:
1. Open a terminal in this folder.
2. Run the web server command:
   ```bash
   source venv/bin/activate
   uvicorn main:app --reload --port 8000
   ```
3. Open your browser and go to: **[http://localhost:8000](http://localhost:8000)**
4. Start typing (or speaking!) to chat.

---

## 3️⃣ Method 3: Using the MCP Inspector (Testing & Debugging)
The **MCP Inspector** is an official tool created by the developers of MCP. It gives you a clean control panel to test each function individually.

### How to run:
To make this extremely simple, we created a one-word shortcut (an alias) in your terminal.
1. Open your terminal.
2. Type:
   ```bash
   mcp-email
   ```
    *(If you haven't set up the alias yet, run the full command listed in the main [README.md](file:///home/heet/Documents/Tarun%20Sir/email-mcp-server/README.md#method-2--shell-script)).*
3. The terminal will print a link that looks like this: `http://localhost:5173` (or similar).
4. Click the link to open it in Google Chrome.
5. Click the **Connect** button, then go to the **Tools** tab.
6. You will see buttons for `list_recent_emails`, `send_email`, and others. You can fill in the parameters and click "Run" to test them instantly.

---

## 🔑 Authenticating Your Emails (Direct Terminal / CLI Mode)
If you do **not** want to use or run the custom Web UI, you can connect/authorize your Gmail or Outlook account directly from the **terminal (Command Line Interface)**!

### Step-by-Step Instructions:
1. Open a terminal in the project folder and activate the environment:
   ```bash
   source venv/bin/activate
   ```
2. Run the authentication script for the account you want to connect:
   * **For Gmail:** `python test_auth.py gmail`
   * **For Outlook:** `python test_auth.py outlook`
3. The script will generate a secure login link and **automatically open your web browser** to Google or Microsoft's authorization page.
4. Log in and click **Allow/Authorize**.
5. Once done, you will be redirected to a callback page (often showing `localhost:8000`). Look at your browser's **address bar** and copy the code parameter after `code=`.
   - *Example:* If the URL is `http://localhost:8000/auth/callback?code=4/0AdyxW5...`, copy `4/0AdyxW5...`.
6. Go back to your terminal, paste the copied code at the prompt, and press **Enter**:
   ```text
   Paste the 'code' value from redirect URL: <PASTE_CODE_HERE>
   ```
7. Once you see the `✅ authenticated!` message, your account is connected securely! Cline or any other MCP client will now be able to access your emails directly without the Web UI running.

---

## 🔌 Other Ways (Claude Desktop, cursor, etc.)
Because this server uses the official **Model Context Protocol (stdio transport)**, you can connect it to any other app that supports MCP:
- **Claude Desktop:** Edit the `claude_desktop_config.json` file as shown in the main [README.md](file:///home/heet/Documents/Tarun%20Sir/email-mcp-server/README.md#claude-desktop-integration).
- **Other IDEs (like Windsurf):** Open settings, look for the MCP/API configuration, and add this server using the same config JSON.
