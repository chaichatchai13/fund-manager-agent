"""
Twilio SMS service — outbound alerts and inbound two-way agent conversation.

Outbound: send_sms(message) → delivers to ALERT_PHONE_NUMBER
Inbound:  handle_incoming(from_number, body) → routes to agent, returns reply text

Two-way flow:
  1. App sends alert SMS: "TSLA down 3.2%. Open sell put? Reply YES to execute."
  2. User replies YES → Twilio POST /webhooks/twilio/sms → handle_incoming()
  3. handle_incoming() detects pending confirmation or routes to agent chat
  4. Returns TwiML response with agent's reply
"""
import structlog

logger = structlog.get_logger(__name__)

# In-memory store for pending trade confirmations (survives only current process)
# Key: phone_number, Value: {"action": "open_sell_put", "symbol": "TSLA", ...}
_pending_confirmations: dict[str, dict] = {}


class SMSService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from app.config import settings
            if not settings.twilio_account_sid or not settings.twilio_auth_token:
                raise RuntimeError("Twilio credentials not configured — set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
            from twilio.rest import Client
            self._client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        return self._client

    async def send_sms(self, message: str, to: str | None = None) -> bool:
        """Send an SMS to the alert phone number (or a specific number)."""
        from app.config import settings
        import asyncio

        to_number = to or settings.alert_phone_number
        from_number = settings.twilio_from_number

        if not to_number or not from_number:
            logger.warning("SMS not sent — phone numbers not configured")
            return False

        try:
            client = self._get_client()
            await asyncio.to_thread(
                client.messages.create,
                body=message,
                from_=from_number,
                to=to_number,
            )
            logger.info("SMS sent", to=to_number[:6] + "****", length=len(message))
            return True
        except Exception as exc:
            logger.error("SMS send failed", error=str(exc))
            return False

    def set_pending_confirmation(self, phone: str, action: dict) -> None:
        """Store a pending trade confirmation waiting for YES/NO reply."""
        _pending_confirmations[phone] = action
        logger.info("Pending confirmation set", phone=phone[:6] + "****", action=action.get("type"))

    def get_pending_confirmation(self, phone: str) -> dict | None:
        return _pending_confirmations.get(phone)

    def clear_pending_confirmation(self, phone: str) -> None:
        _pending_confirmations.pop(phone, None)

    async def handle_incoming(self, from_number: str, body: str) -> str:
        """
        Handle an incoming SMS from the user.
        Returns the reply text (sent back via TwiML).
        """
        text = body.strip()
        logger.info("Incoming SMS", from_number=from_number[:6] + "****", body=text[:50])

        # Check for YES/NO reply to a pending confirmation
        pending = self.get_pending_confirmation(from_number)
        if pending:
            if text.upper() in ("YES", "Y", "CONFIRM", "OK"):
                self.clear_pending_confirmation(from_number)
                return await self._execute_pending_action(pending)
            elif text.upper() in ("NO", "N", "CANCEL", "STOP"):
                self.clear_pending_confirmation(from_number)
                return "Got it — trade cancelled."
            # Fall through to agent if not a clear yes/no

        # Route to conversational agent
        reply = await self._agent_reply(text)
        return reply

    async def _execute_pending_action(self, action: dict) -> str:
        """Execute a confirmed trade action."""
        action_type = action.get("type")
        try:
            if action_type == "open_sell_put":
                symbol = action["symbol"]
                rule_id = action.get("rule_id")
                from app.services.scan_service import scan_service
                from app.db.session import AsyncSessionLocal
                # Find an enabled sell-put rule for this symbol if no rule_id stored
                if not rule_id:
                    from sqlalchemy import select
                    from app.models.rule import SellPutRule
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(
                            select(SellPutRule).where(
                                SellPutRule.symbol == symbol.upper(),
                                SellPutRule.enabled.is_(True),
                            ).limit(1)
                        )
                        rule = result.scalar_one_or_none()
                    rule_id = rule.id if rule else None

                if not rule_id:
                    return f"No enabled sell-put rule found for {symbol}. Create one in the app first."

                positions = await scan_service.run_scan(rule_id=rule_id)
                if positions:
                    return f"✅ Sell put opened on {symbol}. Check the app for details."
                return f"Scan ran for {symbol} but no suitable put found right now (market conditions or no qualifying strikes)."

            return f"Action '{action_type}' executed."
        except Exception as exc:
            logger.error("Failed to execute pending action", error=str(exc))
            return f"❌ Failed to execute: {str(exc)}"

    async def _agent_reply(self, message: str) -> str:
        """Run the message through the conversational agent and return a short reply."""
        try:
            from app.agent.agent import chat
            messages = [{"role": "user", "content": message}]
            reply, _ = await chat(messages)
            # Truncate for SMS (160 chars per segment, keep it concise)
            if len(reply) > 320:
                reply = reply[:317] + "..."
            return reply
        except Exception as exc:
            logger.error("Agent SMS reply failed", error=str(exc))
            return "Sorry, I couldn't process that right now. Check the app."


sms_service = SMSService()
