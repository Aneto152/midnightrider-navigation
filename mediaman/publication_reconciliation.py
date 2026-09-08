"""
Publication reconciliation: manual evidence-based resolution for UNKNOWN publication outcomes.

Defines PublicationEvidenceRecord (immutable evidence), PublicationEvidenceValidator (offline validation),
and PublicationReconciler (state transitions with operator authorization).

No content, no credentials, no network access, no automatic retry, no logging.
"""

from dataclasses import dataclass
from typing import Optional
import re
from mediaman.publication_state import (
    PublicationState,
    PublicationStateRecord,
    PublicationStateStore,
)


@dataclass(frozen=True)
class PublicationEvidenceRecord:
    """Immutable evidence record for UNKNOWN publication reconciliation."""
    publication_id: str
    transition: str
    reason: str
    operator_identity: str
    evidence_reference: str
    optional_telegram_message_id: Optional[str]
    reconciliation_timestamp: str
    safe_decision_classification: str


class PublicationEvidenceValidator:
    """Offline evidence validation; never echoes unsafe values."""

    APPROVED_TRANSITIONS = {"UNKNOWN_TO_SENT_RECONCILED"}
    APPROVED_CLASSIFICATIONS = {
        "manual_ui_search_confirmed",
        "api_query_confirmed",
        "external_monitoring_confirmed",
        "operator_confirmed_delivery",
    }

    CREDENTIAL_PATTERNS = [
        r'token\s*=',
        r'password\s*=',
        r'secret\s*=',
        r'api[_-]?key\s*=',
        r'apikey\s*=',
        r'authorization\s*=',
        r'bearer\s+[a-z0-9]{20,}',
        r'basic\s+[a-z0-9]{20,}',
    ]

    URI_CREDENTIAL_PATTERNS = [
        r'postgres://[^@]*:[^@]*@',
        r'postgresql://[^@]*:[^@]*@',
        r'mysql://[^@]*:[^@]*@',
        r'redis://[^@]*:[^@]*@',
        r'mongodb://[^@]*:[^@]*@',
        r'amqp://[^@]*:[^@]*@',
        r'amqps://[^@]*:[^@]*@',
        r'https://[^@]*:[^@]*@',
        r'http://[^@]*:[^@]*@',
    ]

    @staticmethod
    def validate(
        evidence: PublicationEvidenceRecord,
    ) -> tuple[bool, str]:
        """
        Validate a PublicationEvidenceRecord.

        Returns:
            (True, ""): Valid
            (False, error_code): Invalid (safe classification, no echoed values)
        """
        # 1. Input must be a PublicationEvidenceRecord
        if not isinstance(evidence, PublicationEvidenceRecord):
            return (False, "invalid_type")

        # 2. publication_id must match exactly: ^[0-9a-f]{64}$
        if not isinstance(evidence.publication_id, str):
            return (False, "invalid_publication_id")
        if not re.match(r'^[0-9a-f]{64}$', evidence.publication_id):
            return (False, "invalid_publication_id")

        # 3. transition must equal exactly: UNKNOWN_TO_SENT_RECONCILED
        if evidence.transition not in PublicationEvidenceValidator.APPROVED_TRANSITIONS:
            return (False, "invalid_transition")

        # 4. reason must be non-empty, free of credentials and unsafe control characters
        if not isinstance(evidence.reason, str):
            return (False, "invalid_reason")
        if not evidence.reason:
            return (False, "invalid_reason")

        # Check for credentials in reason
        reason_lower = evidence.reason.lower()
        for pattern in PublicationEvidenceValidator.CREDENTIAL_PATTERNS:
            if re.search(pattern, reason_lower, re.IGNORECASE):
                return (False, "unsafe_content")
        for pattern in PublicationEvidenceValidator.URI_CREDENTIAL_PATTERNS:
            if re.search(pattern, reason_lower, re.IGNORECASE):
                return (False, "unsafe_content")

        # Check for NUL and unsafe control characters
        if '\0' in evidence.reason:
            return (False, "unsafe_content")
        for char in evidence.reason:
            code = ord(char)
            if code < 0x20 and code not in (0x09, 0x0a, 0x0d):  # Allow tab, LF, CR
                return (False, "unsafe_content")

        # 5. operator_identity must be non-empty, <= 128 chars, no credentials, no unsafe control chars
        if not isinstance(evidence.operator_identity, str):
            return (False, "invalid_operator_identity")
        if not evidence.operator_identity:
            return (False, "invalid_operator_identity")
        if len(evidence.operator_identity) > 128:
            return (False, "invalid_operator_identity")

        # Check for credentials in operator_identity
        op_id_lower = evidence.operator_identity.lower()
        for pattern in PublicationEvidenceValidator.CREDENTIAL_PATTERNS:
            if re.search(pattern, op_id_lower, re.IGNORECASE):
                return (False, "unsafe_content")

        # Check for NUL and unsafe control characters
        if '\0' in evidence.operator_identity:
            return (False, "unsafe_content")
        for char in evidence.operator_identity:
            code = ord(char)
            if code < 0x20 and code not in (0x09, 0x0a, 0x0d):
                return (False, "unsafe_content")

        # 6. evidence_reference must match: source:timestamp:reference_id
        if not isinstance(evidence.evidence_reference, str):
            return (False, "invalid_evidence_reference")

        # Pattern: source:YYYY-MM-DDTHH:MM:SSZ:reference_id
        # source must be: manual_ui, monitoring, api_query, backup_log
        # timestamp must be ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ with colons in time)
        # reference_id must be [A-Za-z0-9_.:/-]{1,128}
        pattern = r'^(manual_ui|monitoring|api_query|backup_log):([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z):([A-Za-z0-9_.:/-]{1,128})$'
        match = re.match(pattern, evidence.evidence_reference)
        if not match:
            return (False, "invalid_evidence_reference")

        # Extract and validate the timestamp component
        timestamp_str = match.group(2)  # YYYY-MM-DDTHH:MM:SSZ
        try:
            from datetime import datetime
            # Parse as UTC ISO 8601
            parsed_ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # Verify it's a valid calendar date/time (fromisoformat will reject invalid dates)
            # e.g., 2026-99-99, 2026-02-30, 2026-08-31T25:00:00Z, 2026-08-31T10:61:00Z
        except (ValueError, AttributeError):
            return (False, "invalid_evidence_reference")

        # 7. reconciliation_timestamp must be ISO 8601 UTC with Z terminator
        if not isinstance(evidence.reconciliation_timestamp, str):
            return (False, "invalid_timestamp")
        if not evidence.reconciliation_timestamp.endswith('Z'):
            return (False, "invalid_timestamp")

        try:
            from datetime import datetime
            datetime.fromisoformat(evidence.reconciliation_timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return (False, "invalid_timestamp")

        # 8. optional_telegram_message_id may be None
        if evidence.optional_telegram_message_id is not None:
            if not isinstance(evidence.optional_telegram_message_id, str):
                return (False, "invalid_optional_message_id")
            if not evidence.optional_telegram_message_id:
                return (False, "invalid_optional_message_id")

            # Must contain only safe identifier characters
            if not re.match(r'^[A-Za-z0-9_-]{1,256}$', evidence.optional_telegram_message_id):
                return (False, "invalid_optional_message_id")

            # Check for credentials
            msg_id_lower = evidence.optional_telegram_message_id.lower()
            for pattern in PublicationEvidenceValidator.CREDENTIAL_PATTERNS:
                if re.search(pattern, msg_id_lower, re.IGNORECASE):
                    return (False, "unsafe_content")

            # Check for whitespace or control characters
            if '\0' in evidence.optional_telegram_message_id:
                return (False, "unsafe_content")
            for char in evidence.optional_telegram_message_id:
                code = ord(char)
                if code < 0x20:
                    return (False, "unsafe_content")

        # 9. safe_decision_classification must be one of the four approved values
        if evidence.safe_decision_classification not in PublicationEvidenceValidator.APPROVED_CLASSIFICATIONS:
            return (False, "invalid_safe_decision_classification")

        return (True, "")


class PublicationReconciler:
    """Manual reconciliation for UNKNOWN publication outcomes; operator-authorized transitions only."""

    def __init__(self, state_store: PublicationStateStore):
        """Initialize with the existing PublicationStateStore instance."""
        if not isinstance(state_store, PublicationStateStore):
            raise ValueError("invalid_state_store")
        self.state_store = state_store

    def reconcile_sent(
        self,
        evidence: PublicationEvidenceRecord,
    ) -> PublicationStateRecord:
        """
        Transition UNKNOWN → SENT_RECONCILED with explicit evidence.

        Validates evidence, retrieves publication, requires UNKNOWN state,
        and calls state-store transition with operator_authorized=True.

        Raises:
            ValueError("invalid_evidence"): Evidence validation failed
            ValueError("publication_not_found"): Publication does not exist
            ValueError("reconciliation_requires_unknown"): Publication not in UNKNOWN state
        """
        # 1. Validate evidence
        is_valid, error_code = PublicationEvidenceValidator.validate(evidence)
        if not is_valid:
            raise ValueError("invalid_evidence")

        # 2. Retrieve publication from state store
        publication = self.state_store.get(evidence.publication_id)
        if publication is None:
            raise ValueError("publication_not_found")

        # 3. Require UNKNOWN state
        if publication.state != PublicationState.UNKNOWN:
            raise ValueError("reconciliation_requires_unknown")

        # 4. Call state-store transition API
        result = self.state_store.transition(
            evidence.publication_id,
            PublicationState.SENT_RECONCILED,
            operator_authorized=True,
        )

        return result

    def authorize_retry(
        self,
        publication_id: str,
        operator_identity: str,
        reason: str,
        timestamp: str,
    ) -> PublicationStateRecord:
        """
        Transition UNKNOWN → RETRY_AUTHORIZED → READY with explicit operator authorization.

        Validates inputs, requires UNKNOWN state, and performs two immediate transitions
        without executing any actual retry.

        Raises:
            ValueError("invalid_publication_id"): Publication ID format invalid
            ValueError("invalid_operator_identity"): Operator identity invalid
            ValueError("invalid_reason"): Reason invalid
            ValueError("invalid_timestamp"): Timestamp invalid
            ValueError("publication_not_found"): Publication does not exist
            ValueError("reconciliation_requires_unknown"): Publication not in UNKNOWN state
        """
        # 1. Validate publication_id format
        if not isinstance(publication_id, str):
            raise ValueError("invalid_publication_id")
        if not re.match(r'^[0-9a-f]{64}$', publication_id):
            raise ValueError("invalid_publication_id")

        # 2. Validate operator_identity non-empty
        if not isinstance(operator_identity, str):
            raise ValueError("invalid_operator_identity")
        if not operator_identity:
            raise ValueError("invalid_operator_identity")

        # 3. Validate reason non-empty
        if not isinstance(reason, str):
            raise ValueError("invalid_reason")
        if not reason:
            raise ValueError("invalid_reason")

        # 4. Validate timestamp is ISO 8601 UTC ending in Z
        if not isinstance(timestamp, str):
            raise ValueError("invalid_timestamp")
        if not timestamp.endswith('Z'):
            raise ValueError("invalid_timestamp")

        try:
            from datetime import datetime
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            raise ValueError("invalid_timestamp")

        # 2. Retrieve publication from state store
        publication = self.state_store.get(publication_id)
        if publication is None:
            raise ValueError("publication_not_found")

        # 3. Require UNKNOWN state
        if publication.state != PublicationState.UNKNOWN:
            raise ValueError("reconciliation_requires_unknown")

        # 4. Transition UNKNOWN → RETRY_AUTHORIZED with operator_authorized=True
        r1 = self.state_store.transition(
            publication_id,
            PublicationState.RETRY_AUTHORIZED,
            operator_authorized=True,
        )

        # 5. Immediately transition RETRY_AUTHORIZED → READY
        r2 = self.state_store.transition(
            publication_id,
            PublicationState.READY,
            operator_authorized=False,
        )

        return r2

    def abandon(
        self,
        publication_id: str,
        operator_identity: str,
        reason: str,
        timestamp: str,
    ) -> PublicationStateRecord:
        """
        Transition UNKNOWN → DEAD_LETTER with explicit operator abandonment.

        Validates inputs, requires UNKNOWN state, and marks publication as permanently abandoned.

        Raises:
            ValueError("invalid_publication_id"): Publication ID format invalid
            ValueError("invalid_operator_identity"): Operator identity invalid
            ValueError("invalid_reason"): Reason invalid
            ValueError("invalid_timestamp"): Timestamp invalid
            ValueError("publication_not_found"): Publication does not exist
            ValueError("reconciliation_requires_unknown"): Publication not in UNKNOWN state
        """
        # 1. Validate publication_id format
        if not isinstance(publication_id, str):
            raise ValueError("invalid_publication_id")
        if not re.match(r'^[0-9a-f]{64}$', publication_id):
            raise ValueError("invalid_publication_id")

        # 2. Validate operator_identity non-empty
        if not isinstance(operator_identity, str):
            raise ValueError("invalid_operator_identity")
        if not operator_identity:
            raise ValueError("invalid_operator_identity")

        # 3. Validate reason non-empty
        if not isinstance(reason, str):
            raise ValueError("invalid_reason")
        if not reason:
            raise ValueError("invalid_reason")

        # 4. Validate timestamp is ISO 8601 UTC ending in Z
        if not isinstance(timestamp, str):
            raise ValueError("invalid_timestamp")
        if not timestamp.endswith('Z'):
            raise ValueError("invalid_timestamp")

        try:
            from datetime import datetime
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            raise ValueError("invalid_timestamp")

        # 2. Retrieve publication from state store
        publication = self.state_store.get(publication_id)
        if publication is None:
            raise ValueError("publication_not_found")

        # 3. Require UNKNOWN state
        if publication.state != PublicationState.UNKNOWN:
            raise ValueError("reconciliation_requires_unknown")

        # 4. Transition UNKNOWN → DEAD_LETTER with operator_authorized=True
        result = self.state_store.transition(
            publication_id,
            PublicationState.DEAD_LETTER,
            operator_authorized=True,
        )

        return result
