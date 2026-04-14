# tests/test_alerting.py

import pytest
from unittest.mock import patch, MagicMock
from cw_trading_system.utils.alerting import AlertManager


@pytest.fixture
def alert_manager():
    return AlertManager()


def test_alert_manager_init_no_config(alert_manager):
    # Assuming config is disabled by default
    assert not alert_manager.email_enabled
    assert not alert_manager.sms_enabled


@patch('cw_trading_system.utils.alerting.ALERT_CONFIG')
def test_alert_manager_init_email_enabled(mock_config, alert_manager):
    mock_config.email_enabled = True
    mock_config.email_from = "test@example.com"
    mock_config.email_password = "password"
    mock_config.email_to = "to@example.com"

    with patch('cw_trading_system.utils.alerting.yagmail.SMTP') as mock_yag:
        manager = AlertManager()
        assert manager.email_enabled
        mock_yag.assert_called_once_with("test@example.com", "password")


@patch('cw_trading_system.utils.alerting.ALERT_CONFIG')
def test_alert_manager_init_sms_enabled(mock_config, alert_manager):
    mock_config.sms_enabled = True
    mock_config.twilio_account_sid = "sid"
    mock_config.twilio_auth_token = "token"

    with patch('cw_trading_system.utils.alerting.Client') as mock_client:
        manager = AlertManager()
        assert manager.sms_enabled
        mock_client.assert_called_once_with("sid", "token")


@patch('cw_trading_system.utils.alerting.ALERT_CONFIG')
def test_send_email_alert(mock_config):
    mock_config.email_enabled = True
    mock_config.email_to = "to@example.com"

    with patch('cw_trading_system.utils.alerting.yagmail.SMTP') as mock_yag:
        manager = AlertManager()
        manager.email_enabled = True  # Force enable for test
        manager.yag = MagicMock()
        mock_yag.return_value = manager.yag

        manager.send_email_alert("Subject", "Body")

        manager.yag.send.assert_called_once_with(
            to="to@example.com",
            subject="Subject",
            contents="Body"
        )


@patch('cw_trading_system.utils.alerting.ALERT_CONFIG')
def test_send_sms_alert(mock_config):
    mock_config.sms_enabled = True
    mock_config.twilio_from_number = "+123"
    mock_config.sms_to_number = "+456"

    with patch('cw_trading_system.utils.alerting.Client') as mock_client:
        manager = AlertManager()
        manager.sms_enabled = True  # Force enable for test
        manager.twilio_client = MagicMock()
        mock_client.return_value = manager.twilio_client

        manager.send_sms_alert("Test message")

        manager.twilio_client.messages.create.assert_called_once_with(
            body="Test message",
            from_="+123",
            to="+456"
        )


def test_send_alert_calls_both():
    manager = AlertManager()
    manager.email_enabled = True
    manager.sms_enabled = True

    with patch.object(manager, 'send_email_alert') as mock_email, \
         patch.object(manager, 'send_sms_alert') as mock_sms:

        manager.send_alert("Subject", "Message")

        mock_email.assert_called_once_with("Subject", "Message")
        mock_sms.assert_called_once_with("Message")