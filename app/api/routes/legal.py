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
  <title>SMS Alerts Opt-In — ThetaFlow</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f6f8fa; min-height: 100vh;
            display: flex; align-items: center; justify-content: center; padding: 24px; }}
    .card {{ background: #fff; border: 1px solid #d0d7de; border-radius: 12px;
             padding: 32px; max-width: 480px; width: 100%; }}
    .logo {{ font-size: 22px; font-weight: 700; color: #24292f; margin-bottom: 6px; }}
    .logo span {{ color: #0969da; }}
    .tagline {{ font-size: 13px; color: #57606a; margin-bottom: 24px; }}
    h1 {{ font-size: 20px; color: #24292f; margin-bottom: 8px; }}
    .desc {{ font-size: 14px; color: #444; line-height: 1.6; margin-bottom: 20px; }}
    .bullets {{ margin: 0 0 20px 18px; }}
    .bullets li {{ font-size: 14px; color: #444; margin-bottom: 4px; }}
    label.field {{ display: block; font-size: 13px; font-weight: 600; color: #24292f;
                   margin-bottom: 6px; }}
    input[type=tel] {{ width: 100%; padding: 10px 14px; font-size: 15px;
                       border: 1px solid #d0d7de; border-radius: 8px; outline: none;
                       font-family: inherit; transition: border-color 0.15s; }}
    input[type=tel]:focus {{ border-color: #0969da; box-shadow: 0 0 0 3px rgba(9,105,218,0.15); }}
    .consent-box {{ display: flex; gap: 10px; align-items: flex-start;
                    margin: 16px 0; cursor: pointer; }}
    .consent-box input[type=checkbox] {{ margin-top: 3px; width: 16px; height: 16px;
                                         flex-shrink: 0; cursor: pointer; accent-color: #0969da; }}
    .consent-text {{ font-size: 13px; color: #444; line-height: 1.6; }}
    .consent-text a {{ color: #0969da; }}
    .btn {{ width: 100%; padding: 11px; font-size: 15px; font-weight: 600;
            background: #0969da; color: #fff; border: none; border-radius: 8px;
            cursor: pointer; font-family: inherit; transition: background 0.15s; }}
    .btn:hover {{ background: #0860c8; }}
    .btn:disabled {{ background: #8c959f; cursor: not-allowed; }}
    .freq-note {{ font-size: 12px; color: #57606a; margin-top: 14px; text-align: center; line-height: 1.5; }}
    .freq-note a {{ color: #0969da; }}
    .success {{ display: none; text-align: center; padding: 20px 0; }}
    .success .check {{ font-size: 48px; margin-bottom: 12px; }}
    .success h2 {{ color: #1a7f37; font-size: 18px; margin-bottom: 8px; }}
    .success p {{ font-size: 14px; color: #57606a; line-height: 1.6; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">Theta<span>Flow</span></div>
    <div class="tagline">Private automated options trading system</div>

    <div id="form-section">
      <h1>📱 Subscribe to Account Activity Notifications</h1>
      <p class="desc">
        Receive automated SMS notifications when brokerage account events occur —
        order confirmations, position updates, and account summaries delivered directly
        to your phone by the ThetaFlow application.
      </p>
      <ul class="bullets">
        <li>Order confirmations (placed, filled, or cancelled)</li>
        <li>Position status updates and realized P&amp;L at exit</li>
        <li>Daily account summary (positions &amp; balance)</li>
        <li>Application status alerts (e.g. connection issues)</li>
      </ul>

      <label class="field" for="phone">Mobile Phone Number</label>
      <input type="tel" id="phone" placeholder="+1 (555) 000-0000" autocomplete="tel" />

      <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;padding:14px 16px;margin:16px 0;">
        <label class="consent-box" for="consent" style="margin:0;">
          <input type="checkbox" id="consent" />
          <span class="consent-text">
            <strong>Optional:</strong> By checking this box, I agree to receive recurring
            automated SMS brokerage account notifications from <strong>ThetaFlow</strong>
            (operated by Chatchai Satienpattanakul) at the mobile number provided above.
            Messages are generated automatically by the application when account events occur
            (order fills, position updates, account summaries).
            Message frequency varies — up to <strong>10 messages per trading day</strong>
            based on account activity.
            <strong>Message and data rates may apply.</strong>
            Reply <strong>STOP</strong> to cancel at any time.
            Reply <strong>HELP</strong> for assistance.
            View our <a href="/privacy" target="_blank">Privacy Policy</a> and
            <a href="/terms" target="_blank">Terms of Service</a>.
          </span>
        </label>
      </div>

      <button class="btn" id="submit-btn" disabled onclick="submitForm()">
        Submit
      </button>

      <p class="freq-note">
        SMS consent is optional and not required to use ThetaFlow.<br>
        Msg &amp; data rates may apply &nbsp;·&nbsp; Reply STOP to unsubscribe &nbsp;·&nbsp;
        Reply HELP for help<br>
        <a href="/privacy">Privacy Policy</a> &nbsp;·&nbsp;
        <a href="/terms">Terms of Service</a>
      </p>
    </div>

    <div class="success" id="success-section">
      <div class="check" id="success-icon">✅</div>
      <h2 id="success-title">Submitted!</h2>
      <p id="success-body"></p>
    </div>
  </div>

  <script>
    var checkbox = document.getElementById('consent');
    var phone = document.getElementById('phone');
    var btn = document.getElementById('submit-btn');

    function updateBtn() {{
      btn.disabled = phone.value.trim().length < 7;
    }}
    checkbox.addEventListener('change', updateBtn);
    phone.addEventListener('input', updateBtn);

    function submitForm() {{
      var opted_in = checkbox.checked;
      document.getElementById('form-section').style.display = 'none';
      var section = document.getElementById('success-section');
      section.style.display = 'block';
      if (opted_in) {{
        document.getElementById('success-icon').textContent = '✅';
        document.getElementById('success-title').textContent = 'You’re subscribed!';
        document.getElementById('success-body').innerHTML =
          'SMS account notifications have been enabled for your ThetaFlow account.<br><br>' +
          'Reply <strong>STOP</strong> at any time to unsubscribe.<br>' +
          'Reply <strong>HELP</strong> for assistance.';
      }} else {{
        document.getElementById('success-icon').textContent = '📋';
        document.getElementById('success-title').textContent = 'Phone number saved';
        document.getElementById('success-body').innerHTML =
          'Your phone number has been saved.<br><br>' +
          'SMS notifications were <strong>not</strong> enabled because the consent ' +
          'checkbox was not checked. You can return to this page and resubmit with ' +
          'the checkbox checked to enable SMS alerts.';
      }}
    }}
  </script>
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
  <p><strong>Effective date: May 21, 2026 &nbsp;|&nbsp; Last updated: June 2026</strong></p>

  <p>ThetaFlow ("we", "our", "the application") is a private automated brokerage account
  management application operated by Chatchai Satienpattanakul. The application connects to a
  Charles Schwab brokerage account via API and sends automated SMS notifications when account
  activity occurs. This Privacy Policy explains how personal information is collected, used,
  and protected.</p>

  <h2>1. Information We Collect</h2>
  <ul>
    <li><strong>Phone number</strong> — provided voluntarily through the opt-in form at
        theta-flows.com/sms-optin. Used solely to deliver account activity notifications
        and receive opt-out/help replies.</li>
    <li><strong>Brokerage account data</strong> — fetched from the Charles Schwab API on behalf
        of the account owner. Stored locally in the application database on a private server.</li>
    <li><strong>Push notification tokens</strong> — stored locally to deliver browser push
        notifications to the owner's registered devices.</li>
  </ul>

  <h2>2. SMS / Text Messaging Program</h2>
  <p>ThetaFlow operates an automated SMS notification program that delivers brokerage account
  activity alerts to the registered phone number. Messages are triggered solely by application
  events — no human manually composes or sends any message. By opting in, you consent to
  receive text messages including:</p>
  <ul>
    <li>Brokerage order confirmations (orders placed, filled, or cancelled)</li>
    <li>Open position status updates and realized profit/loss notifications</li>
    <li>Account balance and portfolio summary notifications</li>
    <li>Application status alerts (e.g. connectivity issues requiring attention)</li>
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
    <li>To deliver automated SMS account activity notifications to the registered phone number.</li>
    <li>To process inbound SMS replies (STOP/HELP/UNSTOP) per carrier requirements.</li>
    <li>To display portfolio performance and position data in the private dashboard.</li>
    <li>To operate automated account management rules on behalf of the account owner.</li>
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
  <p><strong>Last updated: June 2026</strong></p>

  <p>ThetaFlow is a private automated brokerage account management application operated by
  Chatchai Satienpattanakul. The application connects to a Charles Schwab brokerage account
  via API and sends automated SMS notifications when account activity occurs. These terms
  govern use of the SMS notification feature.</p>

  <h2>Program Description</h2>
  <p>ThetaFlow sends automated SMS notifications to the registered phone number when brokerage
  account events are triggered by the application. All messages are generated automatically by
  the application — no individual manually composes or sends messages. Notifications include:</p>
  <ul>
    <li>Brokerage order confirmations — when orders are placed, filled, or cancelled</li>
    <li>Open position status updates and realized profit/loss notifications at exit</li>
    <li>Daily account summary — open positions count and portfolio balance</li>
    <li>Application status alerts — e.g. brokerage connection issues requiring attention</li>
  </ul>

  <h2>Message Frequency</h2>
  <p>Message frequency varies based on account activity. Typically 1–10 messages per trading
  day, depending on the number of orders placed and positions managed.</p>

  <h2>Message &amp; Data Rates</h2>
  <p>Message and data rates may apply depending on your mobile carrier plan.</p>

  <h2>Opt-Out Instructions</h2>
  <p>Reply <strong>STOP</strong> to any message to unsubscribe from all SMS notifications.
  You will receive a confirmation message and no further messages will be sent.</p>

  <h2>Help</h2>
  <p>Reply <strong>HELP</strong> to any message for assistance, or contact the application
  owner directly.</p>

  <h2>Privacy Policy</h2>
  <p>Please review our Privacy Policy at
  <a href="https://theta-flows.com/privacy">https://theta-flows.com/privacy</a>.</p>

  <h2>Support Contact</h2>
  <p>For support or questions, contact the application owner directly at
  <a href="mailto:chaisatien13@gmail.com">chaisatien13@gmail.com</a>.</p>

  <h2>Disclaimer</h2>
  <p>ThetaFlow is a personal tool and does not constitute financial advice. All trading
  decisions are the sole responsibility of the account owner. Past performance does not
  guarantee future results.</p>

  <h2>Carriers</h2>
  <p>Carriers are not liable for any delayed or undelivered messages.</p>

  <footer>ThetaFlow &mdash; Private automated trading system &mdash;
  &copy; 2026 Chatchai Satienpattanakul</footer>
</body>
</html>""")
