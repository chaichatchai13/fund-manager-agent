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


@router.get("/sms-optin", response_class=HTMLResponse, include_in_schema=False)
async def sms_optin():
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SMS Opt-In — ThetaFlow Settings</title>
  <style>{_BASE_STYLE}
    .badge {{ display: inline-block; background: #dafbe1; color: #116329; font-size: 11px;
              font-weight: 600; padding: 2px 8px; border-radius: 4px; margin-left: 8px; }}
    .optin-label {{ display: flex; gap: 10px; align-items: flex-start; cursor: pointer;
                    font-size: 14px; line-height: 1.7; color: #24292f; }}
    .optin-label input {{ margin-top: 3px; width: 16px; height: 16px; flex-shrink: 0; }}
    .note {{ background: #fff8c5; border: 1px solid #d4a72c; border-radius: 8px;
             padding: 12px 16px; font-size: 13px; color: #633c01; margin-top: 20px; }}
    .optional {{ font-size: 12px; color: #57606a; font-style: italic; margin-top: 10px; }}
  </style>
</head>
<body>
  <h1>ThetaFlow — SMS Opt-In</h1>
  <p>This page shows the SMS consent section of the ThetaFlow Settings page, accessible after login at
  <a href="https://theta-flows.com">theta-flows.com</a>.</p>

  <div style="background:#fff;border:1px solid #d0d7de;border-radius:12px;padding:24px;margin:24px 0">
    <h2 style="margin:0 0 8px">📱 SMS Trading Alerts <span class="badge">OPTIONAL</span></h2>
    <p>Receive SMS alerts for price movements, position updates, and trade confirmations.
       Reply YES/NO to act on alerts directly from your phone.</p>

    <label class="optin-label">
      <input type="checkbox" id="sms-consent">
      <span>
        I agree to receive SMS trading alerts from <strong>ThetaFlow</strong>.
        Message frequency varies (up to 10 messages per trading day based on market activity).
        Message and data rates may apply.
        Reply <strong>STOP</strong> to unsubscribe at any time.
        Reply <strong>HELP</strong> for help.
        &nbsp;<a href="/privacy">Privacy Policy</a> &nbsp;&middot;&nbsp;
        <a href="/terms">Terms of Service</a>
      </span>
    </label>

    <p class="optional">&#10003; You can use ThetaFlow without SMS alerts &mdash; this consent is completely optional.</p>
  </div>

  <div class="note">
    <strong>Note for reviewers:</strong> ThetaFlow is a single-user private trading application.
    The SMS consent checkbox is <strong>unchecked by default</strong>. The user may save settings
    and use the full application without checking this box. Checking this box is the only way
    SMS alerts are enabled.
  </div>

  <footer>ThetaFlow &mdash; Private automated trading system</footer>
</body>
</html>""")


@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def privacy_policy():
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Privacy Policy — ThetaFlow</title>
  <style>{_BASE_STYLE}
    .highlight {{ background:#f6f8fa; border-left:4px solid #0969da; padding:12px 16px;
                  border-radius:0 6px 6px 0; margin:16px 0; }}
  </style>
</head>
<body>
  <h1>Privacy Policy</h1>
  <p><strong>Effective date: May 21, 2026 &nbsp;|&nbsp; Last updated: May 27, 2026</strong></p>

  <p>ThetaFlow ("we", "our", "the application") is a private, single-user automated options
  trading application operated by Chatchai Satienpattanakul. This Privacy Policy explains how
  personal information is collected, used, and protected.</p>

  <h2>1. Information We Collect</h2>
  <ul>
    <li><strong>Phone number</strong> — provided voluntarily by the application owner to receive
        SMS trading alerts. Used solely to deliver alerts and receive reply confirmations.</li>
    <li><strong>Brokerage account data</strong> — fetched from the Charles Schwab API on behalf
        of the account owner. Stored locally in the application database on a private server.</li>
    <li><strong>Push notification tokens</strong> — stored locally to deliver browser push
        notifications to the owner's registered devices.</li>
  </ul>

  <h2>2. SMS / Text Messaging Program</h2>
  <p>ThetaFlow operates an SMS alert program that sends automated trading notifications to the
  registered phone number. By opting in, you consent to receive text messages including:</p>
  <ul>
    <li>Portfolio position updates and profit/loss notifications</li>
    <li>Stock price movement alerts based on configured thresholds</li>
    <li>Trade confirmation requests requiring a YES or NO reply</li>
    <li>Morning digest and market open summaries</li>
  </ul>
  <p><strong>Message frequency:</strong> Varies based on market activity; typically 1–10 messages
  per trading day.</p>
  <p><strong>Message &amp; data rates may apply</strong> depending on your mobile carrier plan.</p>
  <p><strong>To opt out:</strong> Reply <strong>STOP</strong> to any message at any time.
  You will receive one confirmation message and no further messages will be sent.</p>
  <p><strong>For help:</strong> Reply <strong>HELP</strong> to any message or email
  <a href="mailto:chaisatien13@gmail.com">chaisatien13@gmail.com</a>.</p>

  <h2>3. How We Use Your Information</h2>
  <ul>
    <li>To deliver SMS trading alerts to the registered phone number.</li>
    <li>To process inbound SMS replies (YES/NO confirmations) and execute requested actions.</li>
    <li>To display portfolio performance and position data in the private dashboard.</li>
    <li>To operate automated trading rules on behalf of the account owner.</li>
  </ul>

  <h2>4. Data Sharing and Disclosure</h2>
  <div class="highlight">
    <strong>No mobile information (including phone numbers and SMS opt-in data) will be shared
    with third parties or affiliates for marketing or promotional purposes.</strong>
    Text messaging originator opt-in data and consent will not be shared with any third party
    under any circumstances.
  </div>
  <p>The only external services that receive any data are:</p>
  <ul>
    <li><strong>Twilio Inc.</strong> — receives the destination phone number and message body
        solely to deliver SMS messages. Twilio does not receive any financial or account data.
        See <a href="https://www.twilio.com/legal/privacy" target="_blank">Twilio's Privacy Policy</a>.</li>
    <li><strong>Anthropic PBC</strong> — receives anonymised conversation text for AI agent
        responses. No personally identifiable information or financial account numbers are sent.</li>
    <li><strong>Charles Schwab &amp; Co.</strong> — brokerage API used to read account data and
        place orders on behalf of the account owner only.</li>
  </ul>
  <p>No data is sold, rented, or shared with any other third parties for any purpose.</p>

  <h2>5. Data Storage and Security</h2>
  <p>All personal and financial data is stored in a private, password-protected database on a
  dedicated server controlled solely by the application owner. The server is hosted on Google
  Cloud Platform and protected by HTTPS (TLS 1.2+). No data is stored on third-party databases
  or cloud storage services.</p>

  <h2>6. Data Retention</h2>
  <p>Data is retained as long as the application is actively used. The application owner may
  delete all stored data at any time. SMS opt-in consent records are retained for a minimum
  of 4 years as required by applicable regulations.</p>

  <h2>7. Your Rights and Choices</h2>
  <p>As the sole user of this application, you have full control over all stored data, including
  the right to access, correct, or delete it. You may opt out of SMS notifications at any time
  by replying STOP or by removing your phone number from the application configuration.</p>

  <h2>8. Changes to This Policy</h2>
  <p>We may update this Privacy Policy from time to time. The "Last updated" date at the top of
  this page will reflect any changes. Continued use of the SMS program following an update
  constitutes acceptance of the revised policy.</p>

  <h2>9. Contact</h2>
  <p>For questions or concerns about this Privacy Policy or your data, contact:</p>
  <p><strong>Chatchai Satienpattanakul</strong><br>
  Email: <a href="mailto:chaisatien13@gmail.com">chaisatien13@gmail.com</a><br>
  Website: <a href="https://theta-flows.com">theta-flows.com</a></p>

  <footer>ThetaFlow &mdash; Private automated trading system &mdash;
  &copy; 2026 Chatchai Satienpattanakul</footer>
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
