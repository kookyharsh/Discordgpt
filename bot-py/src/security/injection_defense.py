import re


class InjectionDefense:
    DANGEROUS_SYSTEM_PATTERNS = [
        re.compile(r"ignore (?:all|previous|\s)+ (?:instructions|directives)", re.IGNORECASE),
        re.compile(r"you are now in (?:developer|dan|admin) mode", re.IGNORECASE),
        re.compile(r"grant (?:me|yourself) administrator", re.IGNORECASE),
        re.compile(r"system prompt", re.IGNORECASE),
        re.compile(r"eval\s*\(", re.IGNORECASE),
        re.compile(r"exec\s*\(", re.IGNORECASE),
        re.compile(r"subprocess", re.IGNORECASE),
        re.compile(r"child_process", re.IGNORECASE),
    ]

    @staticmethod
    def sanitize_external_text(text: str) -> str:
        # Strip control characters
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
        return cleaned.strip()

    @classmethod
    def detect_prompt_injection(cls, prompt: str) -> bool:
        return any(pattern.search(prompt) for pattern in cls.DANGEROUS_SYSTEM_PATTERNS)
