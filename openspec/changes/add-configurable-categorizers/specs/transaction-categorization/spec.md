## Purpose

Allow Statement Sensei users to select and configure the transaction categorizer
that best balances local privacy, cost, and categorization accuracy for their data.

## ADDED Requirements

### Requirement: Categorizer selection
The system SHALL present a categorizer selector before statement processing and
SHALL apply the user's selected categorizer to newly processed statements. The
available choices SHALL include rule-based categorization, Google Gemini, and LM
Studio when those categorizers are available.

#### Scenario: User selects a categorizer before uploading
- **WHEN** a user selects LM Studio and uploads a statement
- **THEN** the system categorizes its transactions with the LM Studio configuration
  currently selected in the UI

#### Scenario: User changes the selected categorizer
- **WHEN** a user changes from rule-based categorization to Google Gemini
- **THEN** subsequently processed statements use Google Gemini rather than the
  rule-based categorizer

### Requirement: LM Studio configuration
The system SHALL allow a user selecting LM Studio to configure the OpenAI-compatible
server URL and the model identifier in the web application. The system SHALL require
both values before processing a statement with LM Studio.

#### Scenario: User supplies an LM Studio server and model
- **WHEN** a user enters a server URL and model identifier and processes a statement
- **THEN** the system sends the statement's transaction descriptions to that server
  using the specified model and assigns the returned categories

#### Scenario: LM Studio configuration is incomplete
- **WHEN** a user selects LM Studio without a server URL or model identifier
- **THEN** the system explains that the missing configuration must be supplied and
  does not process the statement with a different categorizer

### Requirement: Editable rule-based categorization
The system SHALL allow a user selecting rule-based categorization to add, edit, and
remove category keyword rules in the web application. The system SHALL apply the
edited rules to subsequently processed statements.

#### Scenario: User adds a merchant keyword
- **WHEN** a user adds a keyword to a category rule and processes a statement whose
  transaction description contains that keyword
- **THEN** the system assigns that transaction to the configured category

#### Scenario: User removes a rule
- **WHEN** a user removes a category rule and processes a statement matching only
  that removed rule
- **THEN** the system does not assign the removed category based on that rule

### Requirement: Categorization configuration consistency
The system SHALL keep categorization results associated with the categorizer and
effective configuration used to produce them. A change to the selected categorizer,
LM Studio server URL, LM Studio model identifier, or rule set SHALL cause the system
to recategorize reused statement uploads rather than present results from a previous
configuration.

#### Scenario: User changes the LM Studio model for an uploaded statement
- **WHEN** a statement has already been processed and the user changes the LM Studio
  model identifier
- **THEN** the system processes that reused statement with the newly selected model
  before displaying its categories

#### Scenario: User changes an existing rule
- **WHEN** a statement has already been processed and the user edits the rules
- **THEN** the system recategorizes that reused statement with the edited rules

### Requirement: Categorization failure visibility
The system SHALL show a user-visible error when the selected categorizer cannot
complete categorization due to invalid configuration, unavailable service, or an
invalid response. The system SHALL NOT silently substitute another categorizer.

#### Scenario: LM Studio server is unavailable
- **WHEN** LM Studio cannot be reached at the configured server URL
- **THEN** the system displays an error identifying the selected LM Studio
  categorizer and preserves the user's configuration for correction or retry

#### Scenario: Categorizer returns invalid categories
- **WHEN** the selected AI categorizer returns a response that cannot provide one
  permitted category for every transaction
- **THEN** the system displays a categorization error and does not report that a
  different categorizer produced the results
