import sys
import webbrowser
from auth.gmail_auth import get_auth_url as gmail_url, is_authenticated as gmail_ok, exchange_code_for_tokens as gmail_exchange
from auth.outlook_auth import get_auth_url as outlook_url, is_authenticated as outlook_ok, exchange_code_for_tokens as outlook_exchange, graph_request

def test_gmail():
    print("\n── Gmail Auth Test ──")
    if gmail_ok():
        print("✅ Gmail already authenticated!")
    else:
        url = gmail_url()
        print(f"\n👉 Open this URL in browser:\n{url}\n")
        webbrowser.open(url)
        code = input("Paste the 'code' value from redirect URL: ").strip()
        gmail_exchange(code)
        print("✅ Gmail authenticated!")

def test_outlook():
    print("\n── Outlook Auth Test ──")
    if outlook_ok():
        print("✅ Outlook already authenticated!")
    else:
        url = outlook_url()
        print(f"\n👉 Open this URL in browser:\n{url}\n")
        webbrowser.open(url)
        code = input("Paste the 'code' value from redirect URL: ").strip()
        outlook_exchange(code)
        print("✅ Outlook authenticated!")

def check_status():
    print("\n── Auth Status ──")
    print(f"  Gmail:   {'✅ connected' if gmail_ok() else '❌ not connected'}")
    print(f"  Outlook: {'✅ connected' if outlook_ok() else '❌ not connected'}")

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "status"
    if arg == "gmail":
        test_gmail()
    elif arg == "outlook":
        test_outlook()
    elif arg == "status":
        check_status()
    else:
        print("Usage: python test_auth.py [gmail|outlook|status]")