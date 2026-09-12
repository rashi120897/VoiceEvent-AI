"""Twilio voice call management service."""

import structlog
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.request_validator import RequestValidator

from app.config import get_settings

logger = structlog.get_logger()


def generate_twiml_connect(ws_url: str) -> str:
    """
    Generate TwiML response that connects the call to a Media Stream WebSocket.

    Args:
        ws_url: WebSocket URL for the media stream.

    Returns:
        TwiML XML string.
    """
    response = VoiceResponse()
    response.say("Please wait while I connect you to the assistant.", voice="Polly.Amy")
    response.pause(length=1)

    connect = Connect()
    connect.stream(url=ws_url)
    response.append(connect)

    twiml = str(response)
    logger.info("TwiML generated", ws_url=ws_url)
    return twiml


def validate_twilio_signature(
    signature: str,
    url: str,
    params: dict,
) -> bool:
    """
    Validate a Twilio webhook request signature.

    Args:
        signature: The X-Twilio-Signature header value.
        url: The full URL of the webhook endpoint.
        params: The POST parameters from the request.

    Returns:
        True if the signature is valid.
    """
    settings = get_settings()
    validator = RequestValidator(settings.twilio_auth_token)
    is_valid = validator.validate(url, params, signature)

    if not is_valid:
        logger.warning("Invalid Twilio webhook signature")

    return is_valid
