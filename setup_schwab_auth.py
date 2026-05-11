"""
One-time Schwab OAuth2 setup script.

Run this ONCE before starting the app to authenticate with Schwab and save the token.
The app will then load the saved token automatically on every restart.

Usage:
    poetry run python setup_schwab_auth.py
"""
import schwab
from app.config import settings

print("=" * 60)
print("Schwab OAuth2 Setup")
print("=" * 60)
print(f"Callback URL : {settings.schwab_callback_url}")
print(f"Token will be saved to: {settings.schwab_token_path}")
print()
print("A browser window will open. Log in to Schwab and authorise the app.")
print("After redirect, copy the full URL from the browser and paste it here.")
print()

client = schwab.auth.easy_client(
    api_key=settings.schwab_app_key,
    app_secret=settings.schwab_app_secret,
    callback_url=settings.schwab_callback_url,
    token_path=settings.schwab_token_path,
)

# Verify it works
resp = client.get_account_numbers()
accounts = resp.json()
print()
print("✅ Authentication successful!")
print(f"   Account hash: {accounts[0]['hashValue'][:8]}***")
print(f"   Token saved to: {settings.schwab_token_path}")
print()
print("You can now start the app with:  poetry run python main.py")
