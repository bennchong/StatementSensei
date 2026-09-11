## Why

Users cannot choose a categorizer from the web application: statement processing is
always forced to use the built-in rules. Users who run models locally need to use an
LM Studio server without sending transaction descriptions to a third party, while
also being able to tune the rule-based fallback for their own merchants.

## What Changes

- Add a categorizer selection control to the web application.
- Add an LM Studio categorizer that calls a user-configured, OpenAI-compatible local
  server and model.
- Add UI controls for editing the rule-based categorizer's category-to-keyword rules.
- Preserve the selected categorizer and its effective configuration when cached
  statements are reused, so results do not become stale after a configuration change.
- Surface configuration and service failures to the user rather than silently using a
  different categorizer.

## Capabilities

### New Capabilities

- `transaction-categorization`: Select, configure, and apply transaction
  categorizers, including local LM Studio inference and editable categorization rules.

### Modified Capabilities

- None.

## Impact

- Affects the Streamlit application and its statement-processing/cache flow.
- Adds an LM Studio OpenAI-compatible HTTP client dependency or integration.
- Adds tests for categorizer configuration, validation, and cache invalidation.
