from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import os
from typing import Protocol

DEFAULT_CATEGORY = "Uncategorized"
DEFAULT_CATEGORIZER_NAME = "noop"
CATEGORIZER_ENV_VAR = "STATEMENTSENSEI_CATEGORIZER"


class TransactionLike(Protocol):
    description: str
    amount: float


class TransactionCategorizer(Protocol):
    name: str

    def categorize(self, transactions: Sequence[TransactionLike]) -> list[str]:
        ...


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
) -> CategorizationResult:
    categorizer = _REGISTRY[categorizer_name] if categorizer_name else get_selected_categorizer()
    categories = categorizer.categorize(transactions)
    return CategorizationResult(categorizer=categorizer.name, categories=categories)


@dataclass(frozen=True)
class NoOpCategorizer:
    name: str = DEFAULT_CATEGORIZER_NAME

    def categorize(self, transactions: Sequence[TransactionLike]) -> list[str]:
        return [DEFAULT_CATEGORY for _ in transactions]


DEFAULT_RULES: dict[str, tuple[str, ...]] = {
    "Groceries": ("grocery", "supermarket", "whole foods", "trader joe"),
    "Dining": ("restaurant", "cafe", "coffee", "diner"),
    "Transport": ("uber", "lyft", "taxi", "train", "bus"),
    "Utilities": ("utility", "electric", "water", "gas", "internet"),
    "Shopping": ("amazon", "walmart", "target", "shop"),
}


@dataclass(frozen=True)
class RuleBasedCategorizer:
    name: str = "rules"
    rules: dict[str, tuple[str, ...]] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rules", self.rules or DEFAULT_RULES)

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
register_categorizer(RuleBasedCategorizer())
