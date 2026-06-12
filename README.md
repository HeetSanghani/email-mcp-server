# 📧 AI Personal Email Assistant (Email MCP Server)

Welcome to your **AI Personal Email Assistant**! This project acts as a bridge that connects your AI helper (like VS Code Cline) directly to your **Gmail** and **Outlook** accounts. 

Once connected, you can manage your email inbox simply by chatting in plain English—no clicking, searching, or manual copy-pasting required!

---

## 🌟 What is this project?
Normally, AI chatbots can't read your files or check your emails because they are closed off. 

This project uses the **Model Context Protocol (MCP)**. Think of MCP as a secure telephone line:
1. **You** ask the AI: *"Do I have any emails about job interviews?"*
2. **The AI** calls this local server over the secure telephone line.
3. **The Server** checks your Gmail/Outlook securely, finds the emails, and reads them back to the AI.
4. **The AI** presents the answers nicely to you.

---

## 🚀 Easy Quick-Start Guide (For Everyone)

To use your AI Email Assistant, you only need to complete **3 simple steps**:

### 1️⃣ Log In to Your Email Accounts (One-Time Setup)
We need to give the server permission to check your mail:
1. Open a terminal in this folder and run the login server:
   ```bash
   source venv/bin/activate
   uvicorn main:app --reload --port 8000
   ```
2. Open your web browser and click these links to sign in:
   - **Sign in to Gmail:** [http://localhost:8000/auth/gmail/start](http://localhost:8000/auth/gmail/start)
   - **Sign in to Outlook:** [http://localhost:8000/auth/outlook/start](http://localhost:8000/auth/outlook/start)
3. Once you sign in, you can close the browser window. The credentials are saved securely on your computer. You won't have to log in again!

---

### 2️⃣ Connect it to VS Code & Cline
Now we tell Cline how to talk to the email server:
1. Open **VS Code**.
2. Click the **Cline extension** icon in the sidebar.
3. Click the **⚙️ Gear Icon** (Settings) at the bottom.
4. Change the **API Provider** to `OpenRouter`.
5. Enter your OpenRouter API Key.
6. Set the **Model ID** to: `google/gemma-4-31b-it:free` (this is 100% free and very smart!).
7. Scroll down to the **Configure MCP Servers** section, click it, and paste this configuration:
   ```json
   {
     "mcpServers": {
       "email-mcp-server": {
         "command": "/home/heet/Documents/Tarun Sir/email-mcp-server/venv/bin/python",
         "args": ["/home/heet/Documents/Tarun Sir/email-mcp-server/run_mcp.py"],
         "env": {},
         "disabled": false,
         "alwaysAllow": []
       }
     }
   }
   ```
8. Click **Done**.

---

### 3️⃣ Talk to your Assistant!
Start a new chat in Cline and ask questions in plain English:
- 💬 *"Show my last 5 emails."*
- 💬 *"Find any emails matching 'DevOps' from yesterday."*
- 💬 *"Write a friendly reply to the email about the job offer."*

---

## 📄 Want to see what operations you can do?
We have created a dedicated, easy-to-read guide listing all the operations you can perform right now. 

👉 **[Read the Operations Guide (OPERATIONS.md)](file:///home/heet/Documents/Tarun%20Sir/email-mcp-server/OPERATIONS.md)**

---

## 🔒 Is it Safe & Secure?
- **No Passwords Stored:** The server never asks for or stores your Gmail or Outlook passwords. It uses secure official log-in keys (OAuth tokens) approved by Google and Microsoft.
- **Strictly Local:** Everything runs directly on your computer. Your email data is never sent to any third-party databases.
- **Easy Disconnect:** To stop the AI from reading your email, simply toggle the switch to `OFF` in the Cline MCP settings.