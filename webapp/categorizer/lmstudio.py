from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import DEFAULT_CATEGORY, DEFAULT_RULES

if TYPE_CHECKING:
    from collections.abc import Sequence


LM_STUDIO_MAX_COMPLETION_TOKENS = 1024


@dataclass(frozen=True)
class LMStudioCategorizer:
    base_url: str = ""
    model: str = ""
    categories: list[str] | None = None
    name: str = "lmstudio"

    def categorize(self, transactions: Sequence[object]) -> list[str]:
        if not transactions:
            return []

        if not self.base_url or not self.model:
            from webapp.categorization import CategorizationError

            raise CategorizationError("LM Studio server URL and model identifier are required.")

        try:
            from openai import APIError, OpenAI
        except ImportError as error:
            from webapp.categorization import CategorizationError

            raise CategorizationError(
                "The openai package is required to use the LM Studio categorizer."
            ) from error

        categories = self.categories or list(DEFAULT_RULES)
        permitted_categories = [*categories, DEFAULT_CATEGORY]
        categories_list = ", ".join(f'"{category}"' for category in permitted_categories)
        client = OpenAI(base_url=self.base_url, api_key="lm-studio")
        results = []
        for transaction in transactions:
            description = getattr(transaction, "description", "") or ""
            prompt = f"""You are a financial transaction categorizer.
Categorize this transaction into exactly one of these categories: {categories_list}.

Transaction:
1. {description}

Respond with a JSON array containing exactly one category.
Only respond with the JSON array, with no other text."""

            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=LM_STUDIO_MAX_COMPLETION_TOKENS,
                    temperature=0,
                    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                )
            except APIError as error:
                from webapp.categorization import CategorizationError

                raise CategorizationError(
                    f"LM Studio could not complete categorization: {error}"
                ) from error

            try:
                content = response.choices[0].message.content
            except (AttributeError, IndexError, TypeError) as error:
                from webapp.categorization import CategorizationError

                raise CategorizationError("LM Studio returned a response without categories.") from error
            try:
                result = json.loads(content or "")
            except json.JSONDecodeError as error:
                from webapp.categorization import CategorizationError

                if getattr(response.choices[0], "finish_reason", None) == "length":
                    raise CategorizationError(
                        "LM Studio exhausted its completion limit before returning categories. "
                        "Disable model reasoning or increase its context limit."
                    ) from error
                raise CategorizationError("LM Studio returned an invalid JSON response.") from error

            if not isinstance(result, list) or len(result) != 1:
                from webapp.categorization import CategorizationError

                raise CategorizationError(
                    "LM Studio returned a category count of {} that does not match the number of input transactions 1.".format(
                        len(result)
                    )
                )
            if not all(
                isinstance(category, str) and category in permitted_categories
                for category in result
            ):
                from webapp.categorization import CategorizationError

                raise CategorizationError("LM Studio returned one or more unsupported categories.")
            results.extend(result)
        return results
