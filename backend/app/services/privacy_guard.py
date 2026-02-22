"""Privacy guard service for PII detection, sensitivity scoring, and data sanitization.

Detects personally identifiable information (PII) in text using regex patterns,
scores sensitivity, masks data before LLM calls, and decides whether to route
to a local LLM for privacy-sensitive content.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Sensitivity threshold: above this score, use local LLM (Ollama)
LOCAL_LLM_THRESHOLD = 0.7

# --- PII Pattern Definitions ---
# Each pattern has: name, regex, weight (contribution to sensitivity score),
# and a mask replacement string.


@dataclass(frozen=True)
class _PIIPattern:
    """Definition of a single PII detection pattern."""

    name: str
    pattern: re.Pattern[str]
    weight: float
    mask: str


_PII_PATTERNS: list[_PIIPattern] = [
    # Taiwan National ID: 1 letter + 9 digits (e.g., A123456789)
    _PIIPattern(
        name="tw_national_id",
        pattern=re.compile(r"\b[A-Z][12]\d{8}\b"),
        weight=0.9,
        mask="[身分證號已遮蔽]",
    ),
    # Taiwan Unified Business Number (統一編號): 8 digits
    _PIIPattern(
        name="tw_business_id",
        pattern=re.compile(r"\b\d{8}\b(?=\s|$|[，。、）\)])"),
        weight=0.4,
        mask="[統編已遮蔽]",
    ),
    # Bank account numbers: 10-16 digits (common Taiwan formats)
    _PIIPattern(
        name="bank_account",
        pattern=re.compile(r"\b\d{3}-?\d{2}-?\d{5,10}\b"),
        weight=0.8,
        mask="[銀行帳號已遮蔽]",
    ),
    # Email addresses
    _PIIPattern(
        name="email",
        pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        weight=0.5,
        mask="[電子郵件已遮蔽]",
    ),
    # Taiwan phone numbers: 09xx-xxx-xxx or 09xxxxxxxx or (0x)xxxx-xxxx
    _PIIPattern(
        name="phone_tw_mobile",
        pattern=re.compile(r"\b09\d{2}-?\d{3}-?\d{3}\b"),
        weight=0.6,
        mask="[手機號碼已遮蔽]",
    ),
    _PIIPattern(
        name="phone_tw_landline",
        pattern=re.compile(r"\(0\d{1,2}\)\s?\d{4}-?\d{4}"),
        weight=0.5,
        mask="[電話號碼已遮蔽]",
    ),
    # Credit card numbers: 4 groups of 4 digits
    _PIIPattern(
        name="credit_card",
        pattern=re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
        weight=0.9,
        mask="[信用卡號已遮蔽]",
    ),
]


@dataclass
class PIIDetectionResult:
    """Result of PII detection on a text."""

    detected_types: list[str] = field(default_factory=list)
    sensitivity_score: float = 0.0
    match_count: int = 0


class PrivacyGuard:
    """Service for detecting PII, scoring sensitivity, and sanitizing text."""

    def __init__(self) -> None:
        self._patterns = _PII_PATTERNS

    def detect(self, text: str) -> PIIDetectionResult:
        """Detect PII in the given text and return detection results."""
        if not text:
            return PIIDetectionResult()

        detected_types: list[str] = []
        max_weight = 0.0
        total_matches = 0

        for pii in self._patterns:
            matches = pii.pattern.findall(text)
            if matches:
                detected_types.append(pii.name)
                total_matches += len(matches)
                max_weight = max(max_weight, pii.weight)

        # Sensitivity score: max weight of detected patterns, boosted slightly
        # by additional match types (capped at 1.0)
        score = 0.0
        if detected_types:
            type_bonus = min(len(detected_types) - 1, 3) * 0.05
            score = min(max_weight + type_bonus, 1.0)

        return PIIDetectionResult(
            detected_types=detected_types,
            sensitivity_score=round(score, 3),
            match_count=total_matches,
        )

    def sanitize(self, text: str) -> str:
        """Mask all detected PII in the text, replacing with Chinese labels."""
        if not text:
            return text

        result = text
        for pii in self._patterns:
            result = pii.pattern.sub(pii.mask, result)

        return result

    def should_use_local_llm(self, text: str) -> bool:
        """Decide whether to route to local LLM based on sensitivity score."""
        detection = self.detect(text)
        use_local = detection.sensitivity_score >= LOCAL_LLM_THRESHOLD
        if use_local:
            logger.info(
                "Privacy guard recommends local LLM: score=%.3f, types=%s",
                detection.sensitivity_score,
                detection.detected_types,
            )
        return use_local
