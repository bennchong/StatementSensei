from __future__ import annotations

from .constants import DEFAULT_CATEGORY, DEFAULT_RULES

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from webapp.categorization import TransactionLike

# ...existing code...

PREDEFINED_CATEGORIES = list(DEFAULT_RULES.keys()) + [DEFAULT_CATEGORY]


@dataclass(frozen=True)
class GeminiCategorizer:
    name: str = "gemini"
    model: str = "gemini-3.6-flash"
    api_key: str | None = None

    def _get_client(self):
        try:
            from google import genai
        except ImportError as e:
            raise ImportError(
                "google-     package is required for GeminiCategorizer. "
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
        categories_list = ", ".join(f'"{c}"' for c in PREDEFINED_CATEGORIES)
        from google.genai import types

        categories = []
        for transaction in transactions:
            description = transaction.description or ""
            prompt = f"""You are a financial transaction categorizer.
Categorize this transaction into exactly one of these categories: {categories_list}.

Transaction:
1. {description}

Use Google Search to identify the merchant before returning "{DEFAULT_CATEGORY}".
Respond with a JSON array containing exactly one category.
Only respond with the JSON array, no other text."""

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are a helpful assistant. You must output your final response strictly as a valid JSON object. Do not include markdown code blocks like ```json.",
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )

            response_text = response.text
            if not response_text:
                details = response.prompt_feedback or response.model_status or "no feedback provided"
                raise ValueError(
                    "Gemini returned no category candidates or text "
                    f"(details: {details})"
                )
            result = json.loads(response_text)

            if not isinstance(result, list) or len(result) != 1:
                raise ValueError(f"Gemini returned {len(result)} categories for 1 transaction")

            if not all(
                isinstance(category, str) and category in PREDEFINED_CATEGORIES
                for category in result
            ):
                raise ValueError("Gemini returned one or more unsupported categories")
            categories.extend(result)
        print(categories)
        return categories