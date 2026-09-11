from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .categorizer.constants import (
    CATEGORIZER_ENV_VAR,
    DEFAULT_CATEGORIZER_NAME,
    DEFAULT_CATEGORY,
    DEFAULT_RULES,
)
from .categorizer.googleai import GeminiCategorizer
from .categorizer.lmstudio import LMStudioCategorizer

if TYPE_CHECKING:
    from collections.abc import Sequence


class TransactionLike(Protocol):
    description: str
    amount: float


class TransactionCategorizer(Protocol):
    name: str

    def categorize(self, transactions: Sequence[TransactionLike]) -> list[str]:
        ...


class CategorizationError(ValueError):
    """Raised when the selected categorizer cannot produce valid categories."""


def _default_rules() -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple((category, tuple(keywords)) for category, keywords in DEFAULT_RULES.items())


@dataclass(frozen=True)
class CategorizerConfiguration:
    name: str = "rules"
    lm_studio_url: str = ""
    lm_studio_model: str = ""
    rules: tuple[tuple[str, tuple[str, ...]], ...] = _default_rules()

    def normalized_rules(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        normalized: list[tuple[str, tuple[str, ...]]] = []
        seen_categories: set[str] = set()
        for category, keywords in self.rules:
            normalized_category = category.strip()
            normalized_keywords = tuple(keyword.strip().lower() for keyword in keywords if keyword.strip())
            if not normalized_category or not normalized_keywords:
                raise CategorizationError("Each rule needs a category and at least one keyword.")
            if normalized_category in seen_categories:
                raise CategorizationError(f"Rule category '{normalized_category}' is listed more than once.")
            seen_categories.add(normalized_category)
            normalized.append((normalized_category, normalized_keywords))
        return tuple(normalized)

    def normalized_lm_studio_url(self) -> str:
        url = self.lm_studio_url.strip().rstrip("/")
        if url and not url.endswith("/v1"):
            return f"{url}/v1"
        return url

    def validate(self) -> None:
        if self.name not in _REGISTRY:
            raise CategorizationError(f"Unknown categorizer: {self.name}.")
        if self.name == "lmstudio":
            if not self.normalized_lm_studio_url():
                raise CategorizationError("LM Studio server URL is required.")
            if not self.lm_studio_model.strip():
                raise CategorizationError("LM Studio model identifier is required.")
        if self.name == "rules":
            self.normalized_rules()

    def cache_signature(self) -> str:
        self.validate()
        payload: dict[str, object] = {"name": self.name}
        if self.name == "lmstudio":
            payload["url"] = self.normalized_lm_studio_url()
            payload["model"] = self.lm_studio_model.strip()
        elif self.name == "rules":
            payload["rules"] = self.normalized_rules()
        return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class CategorizationResult:
    categorizer: str
    categories: list[str]


_REGISTRY: dict[str, TransactionCategorizer] = {}


def register_categorizer(categorizer: TransactionCategorizer) -> None:
    _REGISTRY[categorizer.name] = categorizer


def get_categorizer(name: str) -> TransactionCategorizer:
    return _REGISTRY[name]


def get_selected_categorizer_name() -> str:
    name = os.getenv(CATEGORIZER_ENV_VAR, DEFAULT_CATEGORIZER_NAME)
    if name not in _REGISTRY:
        return DEFAULT_CATEGORIZER_NAME
    return name


def get_selected_categorizer() -> TransactionCategorizer:
    return _REGISTRY[get_selected_categorizer_name()]


def categorize_transactions(
    transactions: Sequence[TransactionLike],
    categorizer_name: str | None = None,
    configuration: CategorizerConfiguration | None = None,
) -> CategorizationResult:
    configuration = configuration or CategorizerConfiguration(
        name=categorizer_name or get_selected_categorizer_name()
    )
    configuration.validate()

    if configuration.name == "rules":
        categorizer: TransactionCategorizer = RuleBasedCategorizer(dict(configuration.normalized_rules()))
    elif configuration.name == "lmstudio":
        categorizer = LMStudioCategorizer(
            base_url=configuration.normalized_lm_studio_url(),
            model=configuration.lm_studio_model.strip(),
            categories=[category for category, _ in configuration.normalized_rules()],
        )
    else:
        categorizer = get_categorizer(configuration.name)

    categories = categorizer.categorize(transactions)
    return CategorizationResult(categorizer=categorizer.name, categories=categories)


@dataclass(frozen=True)
class NoOpCategorizer:
    name: str = DEFAULT_CATEGORIZER_NAME

    def categorize(self, transactions: Sequence[TransactionLike]) -> list[str]:
        return [DEFAULT_CATEGORY for _ in transactions]


@dataclass(frozen=True)
class RuleBasedCategorizer:
    rules: dict[str, tuple[str, ...]]
    name: str = "rules"

    def categorize(self, transactions: Sequence[TransactionLike]) -> list[str]:
        categories: list[str] = []
        for transaction in transactions:
            description = (transaction.description or "").lower()
            category = DEFAULT_CATEGORY
            for category_name, keywords in self.rules.items():
                if any(keyword in description for keyword in keywords):
                    category = category_name
                    break
            categories.append(category)
        return categories


register_categorizer(NoOpCategorizer())
register_categorizer(RuleBasedCategorizer(DEFAULT_RULES))
register_categorizer(GeminiCategorizer())
register_categorizer(LMStudioCategorizer())
