from dataclasses import dataclass

from webapp.categorization import (
    CATEGORIZER_ENV_VAR,
    DEFAULT_CATEGORY,
    DEFAULT_CATEGORIZER_NAME,
    categorize_transactions,
    get_selected_categorizer,
)


@dataclass
class FakeTransaction:
    description: str
    amount: float


def test_get_selected_categorizer_falls_back(monkeypatch):
    monkeypatch.setenv(CATEGORIZER_ENV_VAR, "missing")
    categorizer = get_selected_categorizer()
    assert categorizer.name == DEFAULT_CATEGORIZER_NAME


def test_categorize_transactions_uses_selected(monkeypatch):
    monkeypatch.setenv(CATEGORIZER_ENV_VAR, "rules")
    transactions = [
        FakeTransaction(description="Uber Trip", amount=-12.5),
        FakeTransaction(description="Whole Foods Market", amount=-34.2),
        FakeTransaction(description="Monthly Internet", amount=-55.0),
    ]
    result = categorize_transactions(transactions)
    assert result.categorizer == "rules"
    assert result.categories == ["Transport", "Groceries", "Utilities"]


def test_categorize_transactions_noop(monkeypatch):
    monkeypatch.setenv(CATEGORIZER_ENV_VAR, "noop")
    transactions = [
        FakeTransaction(description="Some Merchant", amount=-8.5),
        FakeTransaction(description="Another Merchant", amount=-19.0),
    ]
    result = categorize_transactions(transactions)
    assert result.categorizer == "noop"
    assert result.categories == [DEFAULT_CATEGORY, DEFAULT_CATEGORY]
