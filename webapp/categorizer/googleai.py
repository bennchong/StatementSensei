from __future__ import annotations

from .constants import DEFAULT_RULES, DEFAULT_CATEGORY, DEFAULT_CATEGORY

import json
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

# ...existing code...

PREDEFINED_CATEGORIES = list(DEFAULT_RULES.keys()) + [DEFAULT_CATEGORY]


@dataclass(frozen=True)
class GeminiCategorizer:
    name: str = "gemini"
    model: str = "gemini-2.0-flash"
    api_key: str | None = None

    def _get_client(self):
        try:
            from google import genai
        except ImportError as e:
            raise ImportError(
                "google-genai package is required for GeminiCategorizer. "
                "Install it with: pip install google-genai"
            ) from e

        api_key = self.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        return genai.Client(api_key=api_key)

    def categorize(self, transactions: Sequence[TransactionLike]) -> list[str]:
        if not transactions:
            return []

        client = self._get_client()

        descriptions = [t.description or "" for t in transactions]
        numbered = "\n".join(f"{i + 1}. {desc}" for i, desc in enumerate(descriptions))
        categories_list = ", ".join(f'"{c}"' for c in PREDEFINED_CATEGORIES)

        prompt = f"""You are a financial transaction categorizer.
Categorize each of the following transaction descriptions into exactly one of these categories: {categories_list}.

Transactions:
{numbered}

Respond with a JSON array of strings, one category per transaction, in the same order.
Example response format: ["Groceries", "Dining", "Uncategorized"]
Only respond with the JSON array, no other text."""

        from google.genai import types

        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)

        if not isinstance(result, list) or len(result) != len(transactions):
            raise ValueError(
                f"Gemini returned {len(result)} categories for {len(transactions)} transactions"
            )

        return [c if c in PREDEFINED_CATEGORIES else DEFAULT_CATEGORY for c in result]