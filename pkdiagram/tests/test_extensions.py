import sys
import logging

import pytest
from mock import patch, MagicMock

from pkdiagram import extensions


class TestSessionTrackingHandler:
    """Test the SessionTrackingHandler logging handler."""

    def test_handler_creation_with_default_level(self):
        """Test that handler is created with default WARNING level."""
        handler = extensions.SessionTrackingHandler()
        assert handler.level == logging.WARNING

    def test_handler_creation_with_custom_level(self):
        """Test that handler is created with custom log level."""
        handler = extensions.SessionTrackingHandler(min_level=logging.INFO)
        assert handler.level == logging.INFO

        handler = extensions.SessionTrackingHandler(min_level=logging.ERROR)
        assert handler.level == logging.ERROR

    def test_handler_emits_to_active_session(self):
        """Test that handler calls _activeSession.log() with correct parameters."""
        # Create a mock session
        mock_session = MagicMock()
        extensions.setActiveSession(mock_session)

        # Create handler with INFO level and simple message-only format
        handler = extensions.SessionTrackingHandler(min_level=logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test warning message",
            args=(),
            exc_info=None,
        )

        # Emit the record
        handler.emit(record)

        # Verify the session's log method was called
        mock_session.log.assert_called_once()
        call_args = mock_session.log.call_args
        assert call_args[0][0] == "Test warning message"
        assert call_args[1]["level"] == logging.WARNING

        # Verify extras dict was passed (fields currently disabled in handler)
        assert "extras" in call_args[1]

        # Clean up
        extensions.setActiveSession(None)

    def test_handler_respects_log_level_filter(self):
        """Test that handler only emits logs at or above its level."""
        mock_session = MagicMock()
        extensions.setActiveSession(mock_session)

        # Create handler with WARNING level
        handler = extensions.SessionTrackingHandler(min_level=logging.WARNING)

        # Create a logger and add our handler
        logger = logging.getLogger("test_logger_filter")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Log at various levels
        logger.debug("Debug message - should not be tracked")
        logger.info("Info message - should not be tracked")
        logger.warning("Warning message - should be tracked")
        logger.error("Error message - should be tracked")

        # Should only have been called twice (WARNING and ERROR)
        assert mock_session.log.call_count == 2

        # Clean up
        logger.removeHandler(handler)
        extensions.setActiveSession(None)

    def test_handler_does_not_emit_when_no_active_session(self):
        """Test that handler does nothing when there is no active session."""
        # Ensure no active session
        extensions.setActiveSession(None)

        # Create handler
        handler = extensions.SessionTrackingHandler(min_level=logging.INFO)

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # This should not raise an error even without an active session
        handler.emit(record)

    def test_handler_handles_formatting_errors_gracefully(self):
        """Test that handler handles errors gracefully without breaking logging."""
        # Create a mock session that raises an error
        mock_session = MagicMock()
        mock_session.log.side_effect = Exception("Simulated error")
        extensions.setActiveSession(mock_session)

        # Create handler
        handler = extensions.SessionTrackingHandler(min_level=logging.INFO)

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # This should not raise an error even though the session raises one
        # The handler should catch the exception internally
        handler.emit(record)

        # Clean up
        extensions.setActiveSession(None)

    def test_handler_formats_message_when_formatter_is_set(self):
        """Test that handler uses formatter when available."""
        mock_session = MagicMock()
        extensions.setActiveSession(mock_session)

        # Create handler with custom formatter
        handler = extensions.SessionTrackingHandler(min_level=logging.INFO)
        handler.setFormatter(logging.Formatter("CUSTOM: %(message)s"))

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Emit the record
        handler.emit(record)

        # Verify the formatted message was used
        call_args = mock_session.log.call_args
        assert call_args[0][0] == "CUSTOM: Test message"

        # Clean up
        extensions.setActiveSession(None)

    def test_handler_uses_raw_message_when_no_formatter(self):
        """Test that handler uses raw message when no formatter is set."""
        mock_session = MagicMock()
        extensions.setActiveSession(mock_session)

        # Create handler without formatter
        handler = extensions.SessionTrackingHandler(min_level=logging.INFO)

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Emit the record
        handler.emit(record)

        # Verify the raw message was used
        call_args = mock_session.log.call_args
        assert call_args[0][0] == "Test message"

        # Clean up
        extensions.setActiveSession(None)
