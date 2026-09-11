## Context

The application has a categorizer registry containing no-op, rule-based, and Gemini
categorizers. The statement parser currently explicitly selects the rule-based
categorizer, while the Streamlit application caches processed files only by document
identity. See proposal.md and the transaction-categorization specification for the
required user-visible behavior.

## Goals / Non-Goals

**Goals:**
- Make the categorizer and its applicable configuration explicit inputs to statement
  processing.
- Support a locally hosted, OpenAI-compatible LM Studio server without requiring an
  LM Studio-specific Python SDK.
- Let users manage the rule-based category-to-keyword mapping from the UI.
- Prevent cached statement results from crossing categorizer configuration changes.

**Non-Goals:**
- Persist categorizer settings or rules beyond the active Streamlit session.
- Discover, start, or manage the LM Studio server or its models.
- Alter the existing Gemini configuration contract.
- Add custom user-defined categories to downstream reports beyond the categories
  represented by the configured rules.

## Decisions

### Model categorization settings as a typed runtime configuration

Pass a categorizer selection and typed configuration object from the Streamlit UI
through the file-processing functions into categorization. The registry remains the
source for available categorizer implementations, while each implementation receives
only its own validated configuration.

This avoids process-wide environment mutation and the current hard-coded rules
selection. An environment-variable-only approach was rejected because the requested
server URL, model, and rules must be adjustable interactively.

### Use LM Studio's OpenAI-compatible chat-completions API

Implement an LM Studio categorizer with the OpenAI client configured to the supplied
base URL and model identifier. It will send the same batch prompt and request a JSON
array response, then validate count and permitted category values before accepting
the result.

This shares the established AI categorization contract and keeps the integration
portable to OpenAI-compatible local servers. Using an LM Studio-specific SDK was
rejected because it would create needless coupling and does not improve the required
request flow.

### Keep configuration in Streamlit session state

Store the current selection, LM Studio fields, and editable rules in session state,
initializing rules from the existing defaults. Render only the controls relevant to
the selected categorizer. Rule editing will validate non-empty category names and
keywords, normalize keyword input, and maintain a deterministic category order.

Session state fits Streamlit's rerun model and prevents configuration from leaking
between users. Durable settings storage was rejected as out of scope and would
require decisions about profiles, persistence location, and sensitive endpoint data.

### Cache by input identity and effective categorization configuration

Construct a stable, immutable cache signature from document identity, categorizer
name, and the effective configuration: normalized LM Studio URL/model or a
deterministically serialized rule mapping. Use that signature for cached
`ProcessedFile` entries.

This avoids stale categories after a setting change without discarding correct
results for an unchanged upload and configuration. Globally clearing session state
was rejected because it would also discard unrelated application state.

### Surface categorization errors at the UI boundary

Categorizer implementations raise specific validation or service errors; the UI
converts those into a clear Streamlit error and does not append a successful-looking
processed file. No automatic fallback is used.

Silent fallback would make local-model outages indistinguishable from successful
categorization and conflicts with the selected-provider contract.

## Risks / Trade-offs

- [A user-configured URL can be malformed or point to an unavailable server] →
  Validate required fields before processing and display connection failures with the
  selected provider identified.
- [Local models can return malformed JSON or unsupported category labels] → Validate
  response structure, transaction count, and categories before creating results.
- [Changing configuration reruns uploads and can increase model calls] → Reuse cached
  results only for an identical effective configuration and make the active provider
  visible before processing.
- [Editable rules can be ambiguous when multiple categories match] → Preserve the
  deterministic configured category order and assign the first matching category.
- [Configured endpoints can be non-local] → Treat the entered URL as user-authorized
  and make the selected provider and configured target visible in the UI.

## Migration Plan

1. Add configuration types and the LM Studio categorizer while retaining existing
   categorizer registrations.
2. Add UI state and controls, then thread the selected configuration through
   processing and cache identity.
3. Add targeted unit and app-flow tests for configuration validation, rule edits,
   LM Studio responses, failures, and cache invalidation.
4. Deploy as an additive change; existing users continue to receive default
   rule-based categorization until choosing another provider.

Rollback consists of removing the UI selection and LM Studio registration, restoring
the existing default rule-based path. No persistent data migration is required.
