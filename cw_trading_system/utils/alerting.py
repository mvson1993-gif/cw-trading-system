# utils/alerting.py

import logging
import yagmail
from twilio.rest import Client
from ..config.settings import ALERT_CONFIG

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages email and SMS alerts for risk breaches and system events."""

    def __init__(self):
        self.email_enabled = ALERT_CONFIG.email_enabled
        self.sms_enabled = ALERT_CONFIG.sms_enabled

        # Email setup
        if self.email_enabled:
            try:
                self.yag = yagmail.SMTP(ALERT_CONFIG.email_from, ALERT_CONFIG.email_password)
                logger.info("Email alerting enabled")
            except Exception as e:
                logger.error(f"Failed to initialize email: {e}")
                self.email_enabled = False

        # SMS setup
        if self.sms_enabled:
            try:
                self.twilio_client = Client(ALERT_CONFIG.twilio_account_sid, ALERT_CONFIG.twilio_auth_token)
                logger.info("SMS alerting enabled")
            except Exception as e:
                logger.error(f"Failed to initialize SMS: {e}")
                self.sms_enabled = False

    def send_email_alert(self, subject, body):
        """Send email alert."""
        if not self.email_enabled:
            return

        try:
            self.yag.send(to=ALERT_CONFIG.email_to, subject=subject, contents=body)
            logger.info(f"Email alert sent: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    def send_sms_alert(self, message):
        """Send SMS alert."""
        if not self.sms_enabled:
            return

        try:
            self.twilio_client.messages.create(
                body=message,
                from_=ALERT_CONFIG.twilio_from_number,
                to=ALERT_CONFIG.sms_to_number
            )
            logger.info(f"SMS alert sent: {message[:50]}...")
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")

    def send_alert(self, subject, message):
        """Send both email and SMS alerts."""
        self.send_email_alert(subject, message)
        self.send_sms_alert(message)


# Global instance
alert_manager = AlertManager()