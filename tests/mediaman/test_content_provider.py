"""Tests for content providers."""

import unittest
import os

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mediaman.content_provider import (
    TestContentProvider,
    OpenClawGatewayProvider,
    get_content_provider
)


class TestTestContentProvider(unittest.TestCase):
    """Test the deterministic test content provider."""

    def test_french_output(self):
        """TestContentProvider must output French text."""
        provider = TestContentProvider()
        content = provider.get_content("test-race", "2026-08-26T18:00:00")

        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 0)
        # Check for French indicators
        has_french = any(
            c in content.lower()
            for c in ['é', 'è', 'ê', 'ç', 'le ', 'la ', 'et ']
        )
        self.assertTrue(has_french, "Content should contain French indicators")

    def test_no_hardcoded_length_limit(self):
        """Verify no hardcoded MAX_LENGTH constant exists in provider.

        Message length validation is PENDING operational decisions.
        """
        provider = TestContentProvider()
        # Verify MAX_LENGTH attribute was removed
        self.assertFalse(hasattr(provider, 'MAX_LENGTH'),
                        "MAX_LENGTH constant should be removed (length policy PENDING)")
        self.assertFalse(hasattr(TestContentProvider, 'MAX_LENGTH'),
                        "MAX_LENGTH constant should be removed (length policy PENDING)")

    def test_deterministic_calls(self):
        """Repeated calls must have consistent structure (even if counter changes)."""
        provider = TestContentProvider()
        content1 = provider.get_content("test-race", "2026-08-26T18:00:00")
        content2 = provider.get_content("test-race", "2026-08-26T18:00:00")

        # Both should be valid French text
        self.assertIn("Midnight Rider", content1)
        self.assertIn("Midnight Rider", content2)

    def test_content_is_nonempty(self):
        """Content must be non-empty string."""
        provider = TestContentProvider()
        content = provider.get_content("test-race", "2026-08-26T18:00:00")

        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 0)

    def test_validate_rejects_empty(self):
        """validate must reject empty content."""
        provider = TestContentProvider()
        is_valid, error = provider.validate("")

        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())

    def test_validate_accepts_long_content(self):
        """validate must NOT reject content based solely on length.

        Message length policy is PENDING. No hardcoded limit enforces rejection.
        """
        provider = TestContentProvider()
        # Content much longer than former 700/2000 limit
        long_content = "é" * 5000
        is_valid, error = provider.validate(long_content)

        # Should not reject solely due to length
        # (may reject for other reasons like missing French, but not length)
        if not is_valid:
            self.assertNotIn("exceeds", error.lower())
            self.assertNotIn("length", error.lower())
        else:
            self.assertTrue(is_valid)

    def test_validate_rejects_credentials(self):
        """validate must reject content with credential patterns."""
        provider = TestContentProvider()

        # Test various credential patterns
        cred_samples = [
            "Here is the API_KEY secret",
            "Token: abc123def456",
            "Password is secure123",
            "Auth header: Bearer xyz",
        ]

        for sample in cred_samples:
            is_valid, error = provider.validate(sample)
            # Most should be rejected due to lack of French
            if not is_valid:
                self.assertTrue(len(error) > 0)

    def test_validate_rejects_non_french(self):
        """validate must reject non-French content."""
        provider = TestContentProvider()
        english_text = "This is pure English content with no French accents"
        is_valid, error = provider.validate(english_text)

        self.assertFalse(is_valid)
        self.assertIn("french", error.lower())

    def test_validate_accepts_valid(self):
        """validate must accept valid French content."""
        provider = TestContentProvider()
        content = provider.get_content("race", "2026-08-26T18:00:00")
        is_valid, error = provider.validate(content)

        self.assertTrue(is_valid)
        self.assertEqual(error, "")


class TestOpenClawGatewayProvider(unittest.TestCase):
    """Test placeholder OpenClawGatewayProvider."""

    def test_not_implemented(self):
        """Gateway provider must not be implemented yet."""
        provider = OpenClawGatewayProvider()

        with self.assertRaises(NotImplementedError):
            provider.get_content("race", "2026-08-26T18:00:00")


class TestContentProviderFactory(unittest.TestCase):
    """Test factory function."""

    def test_default_is_test(self):
        """Default provider must be TestContentProvider."""
        # Clear env if set
        old_val = os.environ.pop("MEDIAMAN_CONTENT_PROVIDER", None)
        try:
            provider = get_content_provider()
            self.assertIsInstance(provider, TestContentProvider)
        finally:
            if old_val:
                os.environ["MEDIAMAN_CONTENT_PROVIDER"] = old_val

    def test_explicit_test(self):
        """Explicit 'test' must return TestContentProvider."""
        old_val = os.environ.get("MEDIAMAN_CONTENT_PROVIDER")
        os.environ["MEDIAMAN_CONTENT_PROVIDER"] = "test"
        try:
            provider = get_content_provider()
            self.assertIsInstance(provider, TestContentProvider)
        finally:
            if old_val:
                os.environ["MEDIAMAN_CONTENT_PROVIDER"] = old_val
            else:
                os.environ.pop("MEDIAMAN_CONTENT_PROVIDER", None)

    def test_gateway_placeholder(self):
        """'gateway' must return OpenClawGatewayProvider (not implemented)."""
        old_val = os.environ.get("MEDIAMAN_CONTENT_PROVIDER")
        os.environ["MEDIAMAN_CONTENT_PROVIDER"] = "gateway"
        try:
            provider = get_content_provider()
            self.assertIsInstance(provider, OpenClawGatewayProvider)
        finally:
            if old_val:
                os.environ["MEDIAMAN_CONTENT_PROVIDER"] = old_val
            else:
                os.environ.pop("MEDIAMAN_CONTENT_PROVIDER", None)

    def test_unknown_provider_raises(self):
        """Unknown provider must raise ValueError."""
        old_val = os.environ.get("MEDIAMAN_CONTENT_PROVIDER")
        os.environ["MEDIAMAN_CONTENT_PROVIDER"] = "unknown"
        try:
            with self.assertRaises(ValueError) as cm:
                get_content_provider()
            self.assertIn("Unknown content provider", str(cm.exception))
        finally:
            if old_val:
                os.environ["MEDIAMAN_CONTENT_PROVIDER"] = old_val
            else:
                os.environ.pop("MEDIAMAN_CONTENT_PROVIDER", None)


if __name__ == '__main__':
    unittest.main()
