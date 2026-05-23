"""
Inbound webhook endpoints.

POST /webhooks/twilio/sms  — receives incoming SMS from Twilio
Returns TwiML XML with the agent's reply.
"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import Response

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/twilio/sms")
async def twilio_sms_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
):
    """
    Twilio sends POST with From (sender number) and Body (message text).
    We handle it and return TwiML XML.
    """
    from app.services.sms_service import sms_service
    from app.config import settings

    # Validate the request is from our alert number (basic security)
    allowed_number = settings.alert_phone_number
    if allowed_number and From != allowed_number:
        logger.warning("SMS from unknown number blocked", from_number=From[:6] + "****")
        return Response(content=_twiml("Sorry, this number is not authorized."), media_type="application/xml")

    reply_text = await sms_service.handle_incoming(From, Body)
    return Response(content=_twiml(reply_text), media_type="application/xml")


def _twiml(message: str) -> str:
    safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{safe}</Message></Response>'
