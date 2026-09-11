from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from webapp.categorization import (
    CATEGORIZER_ENV_VAR,
    CategorizationError,
    CategorizerConfiguration,
    DEFAULT_CATEGORY,
    DEFAULT_CATEGORIZER_NAME,
    categorize_transactions,
    get_categorizer,
    get_selected_categorizer,
    register_categorizer,
)


@dataclass
class FakeTransaction:
    description: str
    amount: float


@dataclass(frozen=True)
class FakeCategorizer:
    name: str = "test-categorizer"

    def categorize(self, transactions):
        return [f"Category {idx}" for idx, _ in enumerate(transactions)]


def test_register_and_get_categorizer():
    custom = FakeCategorizer()
    register_categorizer(custom)
    assert get_categorizer(custom.name) is custom


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


def test_configuration_signature_is_stable_and_changes_with_rules():
    configuration = CategorizerConfiguration(
        rules=(("Dining", (" cafe ",)),),
    )
    equivalent_configuration = CategorizerConfiguration(
        rules=(("Dining", ("cafe",)),),
    )
    changed_configuration = CategorizerConfiguration(
        rules=(("Dining", ("restaurant",)),),
    )

    assert configuration.cache_signature() == equivalent_configuration.cache_signature()
    assert configuration.cache_signature() != changed_configuration.cache_signature()


def test_rule_configuration_categorizes_with_edited_rules():
    transactions = [FakeTransaction(description="Local Bakery", amount=-10)]
    configuration = CategorizerConfiguration(
        rules=(("Treats", ("bakery",)),),
    )

    result = categorize_transactions(transactions, configuration=configuration)

    assert result.categorizer == "rules"
    assert result.categories == ["Treats"]


def test_lm_studio_requires_server_url_and_model():
    with pytest.raises(CategorizationError, match="server URL"):
        CategorizerConfiguration(name="lmstudio", lm_studio_model="local-model").validate()

    with pytest.raises(CategorizationError, match="model identifier"):
        CategorizerConfiguration(name="lmstudio", lm_studio_url="http://localhost:1234/v1").validate()


def test_lm_studio_categorizes_with_configured_server_and_model(monkeypatch):
    captured = {}
    completion_requests = []

    class FakeAPIError(Exception):
        pass

    class FakeCompletions:
        def create(self, **kwargs):
            completion_requests.append(kwargs)
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='["Dining"]'), finish_reason="stop"
                    )
                ]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        SimpleNamespace(APIError=FakeAPIError, OpenAI=FakeOpenAI),
    )
    configuration = CategorizerConfiguration(
        name="lmstudio",
        lm_studio_url="http://localhost:1234/v1/",
        lm_studio_model="local-model",
    )

    result = categorize_transactions(
        [
            FakeTransaction(description="Coffee Shop", amount=-4),
            FakeTransaction(description="Book Store", amount=-20),
        ],
        configuration=configuration,
    )

    assert result.categorizer == "lmstudio"
    assert result.categories == ["Dining", "Dining"]
    assert captured["base_url"] == "http://localhost:1234/v1"
    assert captured["model"] == "local-model"
    assert captured["max_tokens"] == 1024
    assert captured["temperature"] == 0
    assert captured["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert len(completion_requests) == 2
    assert "Coffee Shop" in completion_requests[0]["messages"][0]["content"]
    assert "Book Store" not in completion_requests[0]["messages"][0]["content"]
    assert "Book Store" in completion_requests[1]["messages"][0]["content"]
    assert "Coffee Shop" not in completion_requests[1]["messages"][0]["content"]


def test_lm_studio_adds_v1_to_bare_server_url(monkeypatch):
    captured = {}

    class FakeAPIError(Exception):
        pass

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content='["Dining"]'))]
                    )
                )
            )

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        SimpleNamespace(APIError=FakeAPIError, OpenAI=FakeOpenAI),
    )

    categorize_transactions(
        [FakeTransaction(description="Coffee Shop", amount=-4)],
        configuration=CategorizerConfiguration(
            name="lmstudio",
            lm_studio_url="http://localhost:1234",
            lm_studio_model="local-model",
        ),
    )

    assert captured["base_url"] == "http://localhost:1234/v1"


def test_lm_studio_rejects_invalid_categories(monkeypatch):
    class FakeAPIError(Exception):
        pass

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content='["Invalid"]'))]
                    )
                )
            )

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        SimpleNamespace(APIError=FakeAPIError, OpenAI=FakeOpenAI),
    )

    with pytest.raises(CategorizationError, match="unsupported categories"):
        categorize_transactions(
            [FakeTransaction(description="Coffee Shop", amount=-4)],
            configuration=CategorizerConfiguration(
                name="lmstudio",
                lm_studio_url="http://localhost:1234/v1",
                lm_studio_model="local-model",
            ),
        )


def test_lm_studio_reports_truncated_response(monkeypatch):
    class FakeAPIError(Exception):
        pass

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_: SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(content=""), finish_reason="length"
                            )
                        ]
                    )
                )
            )

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        SimpleNamespace(APIError=FakeAPIError, OpenAI=FakeOpenAI),
    )

    with pytest.raises(CategorizationError, match="exhausted its completion limit"):
        categorize_transactions(
            [FakeTransaction(description="Coffee Shop", amount=-4)],
            configuration=CategorizerConfiguration(
                name="lmstudio",
                lm_studio_url="http://localhost:1234/v1",
                lm_studio_model="local-model",
            ),
        )


def test_lm_studio_rejects_response_without_choices(monkeypatch):
    class FakeAPIError(Exception):
        pass

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_: SimpleNamespace(choices=[]))
            )

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        SimpleNamespace(APIError=FakeAPIError, OpenAI=FakeOpenAI),
    )

    with pytest.raises(CategorizationError, match="without categories"):
        categorize_transactions(
            [FakeTransaction(description="Coffee Shop", amount=-4)],
            configuration=CategorizerConfiguration(
                name="lmstudio",
                lm_studio_url="http://localhost:1234/v1",
                lm_studio_model="local-model",
            ),
        )


def test_lm_studio_rejects_response_with_null_choices(monkeypatch):
    class FakeAPIError(Exception):
        pass

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_: SimpleNamespace(choices=None))
            )

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        SimpleNamespace(APIError=FakeAPIError, OpenAI=FakeOpenAI),
    )

    with pytest.raises(CategorizationError, match="without categories"):
        categorize_transactions(
            [FakeTransaction(description="Coffee Shop", amount=-4)],
            configuration=CategorizerConfiguration(
                name="lmstudio",
                lm_studio_url="http://localhost:1234/v1",
                lm_studio_model="local-model",
            ),
        )
