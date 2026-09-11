## 1. Categorizer configuration and LM Studio integration

- [x] 1.1 Define typed categorizer configuration and stable cache-signature helpers for selected provider, normalized LM Studio settings, and ordered rules; verify focused unit tests cover equivalent and changed configurations.
- [x] 1.2 Implement and register the LM Studio categorizer using the configured OpenAI-compatible server URL and model, with JSON response and category validation; verify unit tests mock successful, malformed, and unavailable-server responses.
- [x] 1.3 Update categorization dispatch to accept the selected provider and validated runtime configuration without changing the existing Gemini behavior; verify existing categorization tests and new provider-selection tests pass.

## 2. Categorizer configuration UI

- [x] 2.1 Add Streamlit session-state initialization and a categorizer selector with options for rules, Gemini, and LM Studio; verify the selected provider is passed into statement processing.
- [x] 2.2 Add conditional LM Studio URL and model fields, including required-field validation and actionable failures; verify incomplete configuration prevents processing and retains entered values.
- [x] 2.3 Add rule editor controls that add, edit, and remove ordered category-keyword rules with input validation; verify edited rules categorize matching transactions and removed rules no longer match.

## 3. Processing consistency and error behavior

- [x] 3.1 Thread effective categorizer configuration through file parsing and cache processed files by document identity plus configuration signature; verify changing provider, model, URL, or rules reprocesses an existing upload while unchanged configuration reuses cached results.
- [x] 3.2 Handle categorizer validation and service errors at the Streamlit boundary without fallback; verify application-flow tests show an error and do not label fallback output as the selected categorizer.

## 4. Validation

- [x] 4.1 Run `pytest tests/test_categorization.py tests/test_app.py` and resolve failures to confirm categorizer behavior and application integration.
- [x] 4.2 Run `openspec validate add-configurable-categorizers --strict` and resolve all proposal, specification, design, and task validation errors.
