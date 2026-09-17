"""
Tests for logging_utils - 179 lines used by five modules and, until now,
covered by nothing.

The point of this module is that a credential must never reach a log file.
That is a security guarantee, so it is tested as one: the assertions check
that no fragment of the input survives, not merely that some marker appears.
"""

import inspect
import logging
import logging.handlers
import os
import tempfile
import unittest

from mediaman.logging_utils import (
    SanitizedMessage, sanitize_chat_id, sanitize_token, setup_service_logger,
)

SECRETS = [
    "1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
    "glsa_AbCdEf0123456789_deadbeef",
    "short", "", "a" * 500, "token=with spaces", "héllo-ünicode-🙂",
]


class TestSanitizeToken(unittest.TestCase):
    def test_no_fragment_of_the_secret_survives(self):
        """
        Fragments that also belong to the marker's own wording are excluded:
        the marker says "credential reference: token", so finding "toke" in it
        proves nothing. Testing a value against text that legitimately contains
        the same letters is the collision trap, not a leak.
        """
        marker_vocabulary = sanitize_token("irrelevant")
        for secret in SECRETS:
            out = sanitize_token(secret)
            self.assertEqual(out, marker_vocabulary)
            for size in (8, 6):
                for start in range(0, max(0, len(secret) - size) + 1):
                    chunk = secret[start:start + size]
                    if len(chunk) == size and chunk not in marker_vocabulary:
                        self.assertNotIn(chunk, out,
                                         f"fragment {chunk!r} survived sanitisation")

    def test_output_is_a_short_constant_marker(self):
        outs = {sanitize_token(s) for s in SECRETS}
        self.assertEqual(len(outs), 1, f"marker varies with the input: {outs}")
        self.assertLessEqual(len(outs.pop()), 64)

    def test_none_is_handled(self):
        self.assertIsInstance(sanitize_token(None), str)


class TestSanitizeChatId(unittest.TestCase):
    def test_chat_id_value_never_appears(self):
        for chat_id in ("-1001234567890", "987654321", -42, 0, None):
            out = sanitize_chat_id(chat_id)
            digits = "".join(c for c in str(chat_id) if c.isdigit())
            if len(digits) >= 4:
                self.assertNotIn(digits, out)

    def test_marker_does_not_leak_the_length(self):
        short = sanitize_chat_id("12345")
        long = sanitize_chat_id("1234567890123456")
        self.assertEqual(short, long)


SENSITIVE_PARAMS = {"chat_id", "token", "api_key", "secret", "password"}
SECRET_CHAT_ID = "-1001234567890"


class TestSanitizedMessage(unittest.TestCase):
    """
    Feed a credential only to the parameters that actually carry one.
    Passing a token where a boolean flag belongs would test nothing:
    startup(dry_run) formatting its own argument is not a leak.
    """

    def _builders(self):
        for name in ("send_attempt", "send_result", "startup", "shutdown",
                     "content_validation", "heartbeat"):
            builder = getattr(SanitizedMessage, name, None)
            if builder is not None:
                yield name, builder, inspect.signature(builder)

    def test_every_builder_returns_a_string(self):
        found = 0
        for name, builder, sig in self._builders():
            kwargs = {p: (SECRET_CHAT_ID if p in SENSITIVE_PARAMS else 1)
                      for p in sig.parameters}
            self.assertIsInstance(builder(**kwargs), str, name)
            found += 1
        self.assertGreaterEqual(found, 6, "builders disappeared from the API")

    def test_a_sensitive_parameter_never_reaches_the_message(self):
        checked = []
        for name, builder, sig in self._builders():
            sensitive = [p for p in sig.parameters if p in SENSITIVE_PARAMS]
            if not sensitive:
                continue
            kwargs = {p: (SECRET_CHAT_ID if p in SENSITIVE_PARAMS else 1)
                      for p in sig.parameters}
            out = builder(**kwargs)
            for param in sensitive:
                self.assertNotIn(SECRET_CHAT_ID, out,
                                 f"{name} leaked its {param} value")
                self.assertNotIn(SECRET_CHAT_ID.lstrip("-"), out,
                                 f"{name} leaked its {param} digits")
                checked.append(f"{name}.{param}")
        self.assertTrue(checked, "no builder exposes a sensitive parameter to check")


class TestServiceLogger(unittest.TestCase):
    def test_logger_writes_into_the_injected_directory(self):
        tmp = tempfile.mkdtemp()
        logger = setup_service_logger("mediaman-test-logger", tmp)
        logger.info("hello")
        for handler in logger.handlers:
            handler.flush()
        files = [f for f in os.listdir(tmp) if f.endswith(".log")]
        self.assertTrue(files, "no log file was created in the injected directory")
        with open(os.path.join(tmp, files[0]), encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("hello", content)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    def test_directory_is_created_when_missing(self):
        tmp = os.path.join(tempfile.mkdtemp(), "deep", "nested")
        logger = setup_service_logger("mediaman-test-logger-2", tmp)
        self.assertTrue(os.path.isdir(tmp))
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    def test_rotation_is_bounded(self):
        tmp = tempfile.mkdtemp()
        logger = setup_service_logger("mediaman-test-logger-3", tmp)
        rotating = [h for h in logger.handlers
                    if isinstance(h, logging.handlers.RotatingFileHandler)]
        for handler in rotating:
            self.assertGreater(handler.maxBytes, 0, "log growth is unbounded")
            self.assertGreaterEqual(handler.backupCount, 1)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
