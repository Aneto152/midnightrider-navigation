"""
Tests for publication contract: PublicationDTO and PublicationValidator.

Eight offline unit tests validating the publication contract immutability,
field validation, timestamp format, publication_id format, and unsafe content rejection.
No network access, no Telegram contact, no credentials.
"""

import unittest
from datetime import datetime
from mediaman.publication_contract import PublicationDTO, PublicationValidator


class TestPublicationContract(unittest.TestCase):
    """Test publication contract: DTO immutability and validator rules."""

    def test_valid_publication_is_accepted(self):
        """Valid publication with all correct fields is accepted."""
        pub = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content="Safe article content about the race.",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_publication_dto_is_immutable(self):
        """PublicationDTO is frozen and cannot be modified."""
        pub = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content="Safe article content about the race.",
            created_at="2026-08-31T22:39:00Z",
        )
        with self.assertRaises(Exception):
            pub.race_id = "race-002"

    def test_publication_id_must_be_lowercase_sha256(self):
        """publication_id must be exactly 64 lowercase hexadecimal characters."""
        # Too short
        pub_short = PublicationDTO(
            publication_id="0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content="Safe content.",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_short)
        self.assertFalse(is_valid)
        self.assertEqual(error, "invalid_publication_id")

        # Uppercase (not allowed)
        pub_upper = PublicationDTO(
            publication_id="0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF",
            race_id="race-001",
            cycle_id="cycle-001",
            content="Safe content.",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_upper)
        self.assertFalse(is_valid)
        self.assertEqual(error, "invalid_publication_id")

        # Non-hex characters
        pub_invalid_chars = PublicationDTO(
            publication_id="0123456789abcdeg0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content="Safe content.",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_invalid_chars)
        self.assertFalse(is_valid)
        self.assertEqual(error, "invalid_publication_id")

    def test_required_fields_must_be_non_empty_strings(self):
        """All five fields must be non-empty strings."""
        # Empty publication_id
        pub_empty_id = PublicationDTO(
            publication_id="",
            race_id="race-001",
            cycle_id="cycle-001",
            content="Safe content.",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_empty_id)
        self.assertFalse(is_valid)
        self.assertEqual(error, "missing_field")

        # Empty race_id
        pub_empty_race = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="",
            cycle_id="cycle-001",
            content="Safe content.",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_empty_race)
        self.assertFalse(is_valid)
        self.assertEqual(error, "missing_field")

        # Non-string field (int)
        pub_int_field = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id=123,  # Invalid: must be string
            content="Safe content.",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_int_field)
        self.assertFalse(is_valid)
        self.assertIn(error, ["invalid_type", "missing_field"])

    def test_created_at_must_be_utc_iso8601(self):
        """created_at must be ISO 8601 UTC format with Z terminator."""
        # Valid UTC ISO 8601
        pub_valid = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content="Safe content.",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_valid)
        self.assertTrue(is_valid)

        # Missing Z terminator
        pub_no_z = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content="Safe content.",
            created_at="2026-08-31T22:39:00",
        )
        is_valid, error = PublicationValidator.validate(pub_no_z)
        self.assertFalse(is_valid)
        self.assertEqual(error, "invalid_timestamp")

        # Invalid format
        pub_bad_format = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content="Safe content.",
            created_at="31-Aug-2026 22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_bad_format)
        self.assertFalse(is_valid)
        self.assertEqual(error, "invalid_timestamp")

    def test_unsafe_content_is_rejected_without_echoing_content(self):
        """Unsafe content is rejected; validator never echoes content."""
        # Token assignment
        pub_token = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content="This has a token = sk-proj-secret123.",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_token)
        self.assertFalse(is_valid)
        self.assertEqual(error, "unsafe_content")
        # Validator does not return the content
        self.assertNotIn("token", error.lower())
        self.assertNotIn("sk-proj", error)

        # Password assignment
        pub_password = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content="password = fakepassword123",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_password)
        self.assertFalse(is_valid)
        self.assertEqual(error, "unsafe_content")

        # NUL character
        pub_nul = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content="Safe content\x00with NUL.",
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_nul)
        self.assertFalse(is_valid)
        self.assertEqual(error, "unsafe_content")

    def test_long_content_is_not_rejected_by_unapproved_length_limit(self):
        """Long content is allowed; no unapproved length limit enforced."""
        long_content = "A" * 800  # Longer than 700 characters
        pub_long = PublicationDTO(
            publication_id="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            race_id="race-001",
            cycle_id="cycle-001",
            content=long_content,
            created_at="2026-08-31T22:39:00Z",
        )
        is_valid, error = PublicationValidator.validate(pub_long)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validator_rejects_non_dto_input(self):
        """Validator rejects non-DTO input."""
        # String instead of DTO
        is_valid, error = PublicationValidator.validate("not a DTO")
        self.assertFalse(is_valid)
        self.assertEqual(error, "invalid_type")

        # Dict instead of DTO
        is_valid, error = PublicationValidator.validate({
            "publication_id": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "race_id": "race-001",
            "cycle_id": "cycle-001",
            "content": "Safe content.",
            "created_at": "2026-08-31T22:39:00Z",
        })
        self.assertFalse(is_valid)
        self.assertEqual(error, "invalid_type")

        # None
        is_valid, error = PublicationValidator.validate(None)
        self.assertFalse(is_valid)
        self.assertEqual(error, "invalid_type")


if __name__ == '__main__':
    unittest.main()
