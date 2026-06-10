from __future__ import annotations

import re

CREDENTIAL_PATTERNS = {
    "MD": r"\bM\.?D\.?\b", "PhD": r"\bPh\.?D\.?\b", "RD": r"\bR\.?D\.?\b",
    "Certified": r"\bCertified\b", "Certified Nutritionist": r"\bCertified\s+Nutritionist\b",
    "Certified Trainer": r"\bCertified\s+(?:Personal\s+)?Trainer\b",
}
TITLE_PATTERNS = {
    "doctor": r"\b(?:Dr\.?|Doctor)\b", "professor": r"\bProfessor\b", "nutritionist": r"\bNutritionist\b",
    "engineer": r"\bEngineer\b", "researcher": r"\bResearcher\b", "coach": r"\bCoach\b",
    "trainer": r"\bTrainer\b", "consultant": r"\bConsultant\b", "founder": r"\bFounder\b",
    "author": r"\bAuthor\b", "speaker": r"\bSpeaker\b", "creator": r"\bCreator\b",
    "journalist": r"\bJournalist\b", "public figure": r"\bPublic\s+Figure\b",
}
AUTHORITY_PATTERN = re.compile(r"\b(?:board[- ]certified|licensed|peer[- ]reviewed|university|institute|association|government|hospital|published in|featured in|award[- ]winning)\b", re.IGNORECASE)


def extract_credentials(text: str) -> list[str]:
    found = [name for name, pattern in CREDENTIAL_PATTERNS.items() if re.search(pattern, text or "", re.IGNORECASE)]
    if "Certified Nutritionist" in found and "Certified" in found:
        found.remove("Certified")
    return found


def extract_professional_titles(text: str) -> list[str]:
    return [name for name, pattern in TITLE_PATTERNS.items() if re.search(pattern, text or "", re.IGNORECASE)]


def extract_authority_mentions(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0) for match in AUTHORITY_PATTERN.finditer(text or "")))
