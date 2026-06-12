# 🔑 Gmail & Outlook API Keys Setup Guide

This guide walks you through setting up your developers' keys on Google Cloud and Microsoft Azure. You only need to do this once. These keys allow the AI to connect securely to your Gmail and Outlook accounts.

---

## 🅰️ Google Cloud Setup (For Gmail)

### Step 1 — Create a Google Developer Project
1. Open your web browser and go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Log in with your standard Gmail account.
3. Click the dropdown menu at the top left next to "Google Cloud" (it might show "Select a project") and click **"New Project"**.
4. Name the project `Email AI Assistant` and click **"Create"**.
5. Make sure your new project is selected in the top dropdown.

### Step 2 — Enable the Gmail API
1. In the top search bar, search for `Gmail API`.
2. Click on the result that says **"Gmail API"** (under Marketplace/APIs).
3. Click the blue **"Enable"** button.

### Step 3 — Configure the OAuth Consent Screen
1. On the left sidebar, click **"APIs & Services"** and then select **"OAuth consent screen"**.
2. Select **"External"** for the User Type and click **"Create"**.
3. Fill in the required fields:
   - **App Name:** `Email AI Assistant`
   - **User support email:** Select your Gmail address from the dropdown.
   - **Developer contact information:** Type your email address.
4. Click **"Save and Continue"**.
5. **Scopes Screen:** Click **"Save and Continue"** (we will configure scopes dynamically in code).

### Step 4 — Add Test Users (CRITICAL ⚠️)
Because your Google app is in "Testing mode," Google will block logins unless you specifically register your email as a tester.
1. Under the **"Test users"** section, click **"+ Add Users"**.
2. Type your Gmail email address (e.g., `yourname@gmail.com`).
3. Click **"Save"**, then click **"Save and Continue"**.

### Step 5 — Create Web Client Keys
1. On the left sidebar, click **"Credentials"**.
2. Click the **"+ Create Credentials"** button at the top and select **"OAuth client ID"**.
3. Under **Application type**, select **"Web application"**.
4. In the **Name** field, type `Email Server Login`.
5. Scroll down to **Authorized redirect URIs** (do NOT use redirect origins) and click **"+ Add URI"**.
6. Type exactly this address:
   ```text
   http://localhost:8000/auth/gmail/callback
   ```
   *(Ensure there is no space or spelling mistake—this redirect URI must match the code exactly!)*
7. Click **"Create"**.
8. A popup will show your **Client ID** and **Client Secret**. Copy these values!
9. Open your project's `.env` file and paste them here:
   ```env
   GOOGLE_CLIENT_ID=your_copied_client_id
   GOOGLE_CLIENT_SECRET=your_copied_client_secret
   ```

---

## 🅱️ Microsoft Azure Setup (For Outlook)

### Step 1 — Register a Microsoft Application
1. Go to the [Microsoft Azure Portal](https://portal.azure.com/).
2. Log in with your Microsoft/Outlook/Hotmail account.
3. In the search bar at the top, search for `Microsoft Entra ID` (previously called Azure Active Directory).
4. On the left menu, click **"App registrations"** and click **"+ New registration"**.
5. Fill out the registration:
   - **Name:** `Email AI Assistant`
   - **Supported account types:** Select **"Accounts in any organizational directory and personal Microsoft accounts"** (the 3rd option).
   - **Redirect URI:** Select **"Web"** from the dropdown, and type exactly:
     ```text
     http://localhost:8000/auth/outlook/callback
     ```
6. Click **"Register"**.

### Step 2 — Copy the Client ID
1. Once registered, you will see an **Overview** page.
2. Find the **Application (client) ID** (a long string of numbers and letters).
3. Copy it and paste it into your `.env` file:
   ```env
   MICROSOFT_CLIENT_ID=your_copied_client_id
   ```

### Step 3 — Generate a Client Secret
1. On the left sidebar of the Azure portal, click **"Certificates & secrets"**.
2. Click the **"Client secrets"** tab, then click **"+ New client secret"**.
3. Add a description (e.g., `Login Secret`) and select an expiration time (e.g., 180 days).
4. Click **"Add"**.
5. ⚠️ **IMPORTANT:** You will see two values: "Value" and "Secret ID". 
   - **Copy the "Value"** column (a string of letters/symbols).
   - *Do NOT copy the "Secret ID" (that is just a placeholder name).*
6. Paste the Value into your `.env` file:
   ```env
   MICROSOFT_CLIENT_SECRET=your_copied_secret_value
   ```

### Step 4 — Add API Permissions
1. On the left sidebar, click **"API permissions"**.
2. Click **"+ Add a permission"** and select **"Microsoft Graph"**.
3. Click **"Delegated permissions"**.
4. Search for and check these permissions:
   - `Mail.Read`
   - `Mail.Send`
   - `Mail.ReadWrite`
   - `User.Read`
   - `offline_access` *(Allows the AI to stay logged in even when you restart the computer)*
5. Click **"Add permissions"** at the bottom.
