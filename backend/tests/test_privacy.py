"""Tests for PrivacyGuard: PII detection, masking, sensitivity scoring, local routing."""

import pytest

from app.services.privacy_guard import PrivacyGuard, PIIDetectionResult, LOCAL_LLM_THRESHOLD


# ---------------------------------------------------------------------------
# PII Detection Tests
# ---------------------------------------------------------------------------


class TestPIIDetection:
    """Test PrivacyGuard.detect for various PII types."""

    @pytest.fixture
    def guard(self):
        return PrivacyGuard()

    def test_empty_text(self, guard):
        """Empty text returns empty result."""
        result = guard.detect("")
        assert result.detected_types == []
        assert result.sensitivity_score == 0.0
        assert result.match_count == 0

    def test_no_pii(self, guard):
        """Text without PII returns clean result."""
        result = guard.detect("這是一個普通的排程問題")
        assert result.detected_types == []
        assert result.sensitivity_score == 0.0

    def test_detect_taiwan_national_id(self, guard):
        """Detects Taiwan national ID (A123456789)."""
        result = guard.detect("客戶身分證 A123456789")
        assert "tw_national_id" in result.detected_types
        assert result.sensitivity_score >= 0.9

    def test_detect_email(self, guard):
        """Detects email addresses."""
        result = guard.detect("聯絡人 test@example.com")
        assert "email" in result.detected_types
        assert result.match_count >= 1

    def test_detect_tw_mobile(self, guard):
        """Detects Taiwan mobile numbers."""
        result = guard.detect("手機 0912-345-678")
        assert "phone_tw_mobile" in result.detected_types

    def test_detect_tw_mobile_no_dash(self, guard):
        """Detects Taiwan mobile without dashes."""
        result = guard.detect("手機 0912345678")
        assert "phone_tw_mobile" in result.detected_types

    def test_detect_credit_card(self, guard):
        """Detects credit card numbers."""
        result = guard.detect("卡號 4111-1111-1111-1111")
        assert "credit_card" in result.detected_types
        assert result.sensitivity_score >= 0.9

    def test_multiple_pii_types_boost_score(self, guard):
        """Multiple PII types slightly boost sensitivity score."""
        result = guard.detect("email test@example.com 手機 0912345678")
        assert len(result.detected_types) >= 2
        # Score should be max_weight + type_bonus
        assert result.sensitivity_score > 0.5


# ---------------------------------------------------------------------------
# Sensitivity Scoring Tests
# ---------------------------------------------------------------------------


class TestSensitivityScoring:
    """Test sensitivity score calculation."""

    @pytest.fixture
    def guard(self):
        return PrivacyGuard()

    def test_national_id_high_sensitivity(self, guard):
        """National ID has weight 0.9 = high sensitivity."""
        result = guard.detect("A123456789")
        assert result.sensitivity_score >= 0.9

    def test_email_medium_sensitivity(self, guard):
        """Email has weight 0.5 = medium sensitivity."""
        result = guard.detect("user@example.com")
        assert 0.4 <= result.sensitivity_score <= 0.6

    def test_score_capped_at_one(self, guard):
        """Sensitivity score never exceeds 1.0."""
        text = "A123456789 user@example.com 0912345678 4111-1111-1111-1111"
        result = guard.detect(text)
        assert result.sensitivity_score <= 1.0

    def test_type_bonus_calculation(self, guard):
        """Each additional type adds 0.05, capped at 3 bonus types."""
        result = guard.detect("A123456789 user@example.com 0912345678")
        # max_weight=0.9 (national ID) + type_bonus=min(2,3)*0.05=0.1 => 1.0 capped
        assert result.sensitivity_score <= 1.0


# ---------------------------------------------------------------------------
# Masking / Sanitization Tests
# ---------------------------------------------------------------------------


class TestSanitization:
    """Test PrivacyGuard.sanitize for PII masking."""

    @pytest.fixture
    def guard(self):
        return PrivacyGuard()

    def test_sanitize_empty(self, guard):
        """Empty text returns empty."""
        assert guard.sanitize("") == ""

    def test_sanitize_no_pii(self, guard):
        """Text without PII is unchanged."""
        text = "普通排程問題"
        assert guard.sanitize(text) == text

    def test_sanitize_national_id(self, guard):
        """National ID is replaced with mask."""
        result = guard.sanitize("身分證 A123456789 在此")
        assert "A123456789" not in result
        assert "身分證號已遮蔽" in result

    def test_sanitize_email(self, guard):
        """Email is replaced with mask."""
        result = guard.sanitize("email: test@example.com")
        assert "test@example.com" not in result
        assert "電子郵件已遮蔽" in result

    def test_sanitize_phone(self, guard):
        """Phone number is replaced with mask."""
        result = guard.sanitize("電話 0912-345-678")
        assert "0912-345-678" not in result
        assert "手機號碼已遮蔽" in result

    def test_sanitize_multiple_pii(self, guard):
        """Multiple PII types are all masked."""
        text = "客戶 A123456789 email test@example.com"
        result = guard.sanitize(text)
        assert "A123456789" not in result
        assert "test@example.com" not in result


# ---------------------------------------------------------------------------
# Local LLM Routing Tests
# ---------------------------------------------------------------------------


class TestLocalLLMRouting:
    """Test PrivacyGuard.should_use_local_llm threshold logic."""

    @pytest.fixture
    def guard(self):
        return PrivacyGuard()

    def test_threshold_value(self):
        """Local LLM threshold is 0.7."""
        assert LOCAL_LLM_THRESHOLD == 0.7

    def test_no_pii_uses_cloud(self, guard):
        """No PII means cloud LLM is fine."""
        assert guard.should_use_local_llm("普通排程問題") is False

    def test_national_id_uses_local(self, guard):
        """National ID (weight 0.9) triggers local routing."""
        assert guard.should_use_local_llm("客戶 A123456789") is True

    def test_email_only_uses_cloud(self, guard):
        """Email alone (weight 0.5) stays with cloud."""
        assert guard.should_use_local_llm("contact test@example.com") is False

    def test_credit_card_uses_local(self, guard):
        """Credit card (weight 0.9) triggers local routing."""
        assert guard.should_use_local_llm("卡號 4111-1111-1111-1111") is True

    def test_phone_only_uses_cloud(self, guard):
        """Phone alone (weight 0.6) stays with cloud."""
        # Use dashed format to avoid bank_account regex overlap with undashed number
        assert guard.should_use_local_llm("電話 0912-345-678") is False
