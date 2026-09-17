import hashlib
import json
import secrets
from typing import Any


class PlanHasher:
    @staticmethod
    def compute_hash(action_plan: Any) -> str:
        serialized = json.dumps(action_plan, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_nonce() -> str:
        return secrets.token_hex(16)
