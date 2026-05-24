"""
Legal pages — Privacy Policy and Terms of Service.
Served at /privacy and /terms (public, no auth required).
Used for Twilio 10DLC campaign registration.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["legal"])

_BASE_STYLE = """
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         max-width: 760px; margin: 48px auto; padding: 0 24px;
         color: #24292f; line-height: 1.7; }
  h1 { font-size: 28px; border-bottom: 1px solid #d0d7de; padding-bottom: 12px; }
  h2 { font-size: 18px; margin-top: 32px; }
  p, li { font-size: 15px; color: #444; }
  a { color: #0969da; }
  footer { margin-top: 48px; font-size: 12px; color: #888; border-top: 1px solid #eee; padding-top: 16px; }
"""


@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def privacy_policy():
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Privacy Policy — ThetaFlow</title>
  <style>{_BASE_STYLE}</style>
</head>
<body>
  <h1>Privacy Policy</h1>
  <p><strong>Last updated: May 2026</strong></p>

  <p>ThetaFlow is a private, single-user automated options trading application. This policy explains
  how personal data is handled within the system.</p>

  <h2>1. Data We Collect</h2>
  <ul>
    <li><strong>Phone number</strong> — provided by the application owner in the system configuration.
        Used solely to deliver trading alerts and receive reply confirmations via SMS.</li>
    <li><strong>Trading account data</strong> — fetched from the Charles Schwab brokerage API on behalf
        of the account owner. Stored locally in the application database.</li>
    <li><strong>Push notification subscription tokens</strong> — stored locally to deliver browser push
        notifications to the owner's devices.</li>
  </ul>

  <h2>2. How We Use Data</h2>
  <ul>
    <li>To send SMS alerts about portfolio positions, price movements, and trade opportunities.</li>
    <li>To receive and process reply confirmations (YES/NO) for automated trade actions.</li>
    <li>To display account performance and position data in the dashboard.</li>
  </ul>

  <h2>3. Data Sharing</h2>
  <p>No personal data is shared with third parties for marketing or any other purposes.
  The only external services used are:</p>
  <ul>
    <li><strong>Twilio</strong> — for SMS delivery only.</li>
    <li><strong>Anthropic</strong> — for AI agent responses (no PII is sent).</li>
    <li><strong>Charles Schwab API</strong> — for brokerage account access.</li>
  </ul>

  <h2>4. Data Retention</h2>
  <p>All data is stored in a private database controlled solely by the application owner.
  Data is retained as long as the application is running and can be deleted at any time
  by the owner.</p>

  <h2>5. Your Rights</h2>
  <p>As the sole user of this application, you have full control over all data.
  You may opt out of SMS notifications at any time by replying <strong>STOP</strong> to any message
  or by removing your phone number from the application configuration.</p>

  <h2>6. Contact</h2>
  <p>For questions about this policy, contact the application owner directly.</p>

  <footer>ThetaFlow — Private automated trading system</footer>
</body>
</html>""")


@router.get("/terms", response_class=HTMLResponse, include_in_schema=False)
async def terms_of_service():
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Terms of Service — ThetaFlow</title>
  <style>{_BASE_STYLE}</style>
</head>
<body>
  <h1>Terms of Service</h1>
  <p><strong>Last updated: May 2026</strong></p>

  <p>ThetaFlow is a private, single-user automated options trading system operated by and for
  the application owner only. These terms govern use of the SMS notification feature.</p>

  <h2>Program Description</h2>
  <p>ThetaFlow sends automated SMS alerts to the registered phone number for the following purposes:</p>
  <ul>
    <li>Stock price movement alerts</li>
    <li>Options position updates and profit/loss notifications</li>
    <li>Trade confirmation requests requiring a YES or NO reply</li>
    <li>Morning portfolio digest and market open alerts</li>
  </ul>

  <h2>Message Frequency</h2>
  <p>Message frequency varies based on market activity and configured alert thresholds.
  Typically 1–10 messages per trading day.</p>

  <h2>Message &amp; Data Rates</h2>
  <p>Message and data rates may apply depending on your mobile carrier plan.</p>

  <h2>Opt-Out Instructions</h2>
  <p>Reply <strong>STOP</strong> to any message to unsubscribe from all SMS notifications.
  You will receive a confirmation message and no further messages will be sent.</p>

  <h2>Help</h2>
  <p>Reply <strong>HELP</strong> to any message for assistance, or contact the application
  owner directly.</p>

  <h2>Support Contact</h2>
  <p>For support or questions, contact the application owner directly.</p>

  <h2>Disclaimer</h2>
  <p>ThetaFlow is a personal tool and does not constitute financial advice. All trading
  decisions are the sole responsibility of the account owner. Past performance does not
  guarantee future results.</p>

  <footer>ThetaFlow — Private automated trading system</footer>
</body>
</html>""")
