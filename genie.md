# Genie API: Programmatic Access and Lab 6 Testing

## The Genie API Exists and Covers the Full Lifecycle

Databricks exposes a complete REST API for Genie under `/api/2.0/genie/`. The API supports space management, conversations, query results, feedback, and evaluation benchmarks. Every operation available in the web UI has a programmatic equivalent.

### Space Management

Creating a Genie space programmatically requires two things: a warehouse ID and a serialized space definition. The serialized space is a version-2 JSON string containing the full configuration: table references, sample questions, text instructions, example question-SQL pairs, UDF references, join specifications, SQL snippets for filters and expressions, and benchmark questions for evaluation. The `POST /api/2.0/genie/spaces` endpoint accepts this payload alongside optional title, description, and parent path fields.

The practical path to building the serialized space definition is to configure a Genie space manually in the UI first, then call `GET /api/2.0/genie/spaces/{space_id}` with `include_serialized_space=true` to retrieve the full configuration. That retrieved JSON becomes the template for programmatic creation. Spaces can also be updated (`PATCH`) and trashed (`POST .../trash`).

### Conversations and Queries

The conversation API follows a submit-poll-retrieve pattern. A `POST` to `/start-conversation` sends a natural language question and returns a message ID. Polling `GET .../messages/{message_id}` reveals the message status as it progresses through stages: SUBMITTED, FETCHING_METADATA, FILTERING_CONTEXT, ASKING_AI, PENDING_WAREHOUSE, EXECUTING_QUERY, and finally COMPLETED. Once complete, the message contains attachments with generated SQL, and a separate endpoint retrieves the query results. Follow-up questions within the same conversation maintain context from prior messages.

### Evaluation and Benchmarks

A set of beta endpoints support running evaluations against benchmark questions defined in the space configuration. These allow creating eval runs, polling their status, and retrieving per-question results, which opens a path toward automated quality assurance of Genie spaces.

### Limits and Prerequisites

Spaces support up to 10,000 active conversations. Query results return at most 5,000 rows per request (with a separate download endpoint for larger results). The API requires Databricks SQL entitlement, CAN USE permission on a Pro or Serverless SQL warehouse, and Databricks Assistant must be enabled in the workspace.

---

## SDK and CLI Coverage

### Python SDK

The `databricks-sdk` package exposes Genie through `w.genie` on the `WorkspaceClient`. The SDK wraps every REST endpoint and adds convenience methods. The most useful are the `*_and_wait` variants: `start_conversation_and_wait` and `create_message_and_wait` handle the polling loop internally with a configurable timeout (default 20 minutes), returning a completed `GenieMessage` with attachments, generated SQL, and suggested follow-up questions.

Space creation is available as `w.genie.create_space(warehouse_id, serialized_space, ...)`. The SDK also exposes the evaluation methods (`genie_create_eval_run`, `genie_get_eval_run`, `genie_list_eval_results`) added in version 0.98.0.

One known gap: the public API does not return the narrative text summary that the web UI displays. The web UI uses an internal endpoint that includes a `final_summary.result_summary` field not exposed in the public API. The `text` attachment type exists in the SDK dataclass but is not reliably populated.

### Databricks CLI

The CLI supports conversation operations under `databricks genie`: starting conversations, sending follow-up messages, retrieving messages and query results. However, the CLI does not currently support space creation or listing. Space management requires the REST API or Python SDK directly.

### Databricks Asset Bundles

There is no official support for Genie spaces as a DABs resource type. A community pull request exists to add `genie_spaces` as a bundle resource, but it has not been merged. The Terraform provider also lacks a `databricks_genie_space` resource. Deploying Genie spaces as infrastructure-as-code is not yet possible through the standard toolchain.

---

## AI Dev Kit Patterns

The Databricks AI Dev Kit repository contains a dedicated Genie skill and MCP tools that demonstrate programmatic Genie management in practice. Five MCP tools handle the full lifecycle: create or update a space, get space details, delete a space, migrate (export/import) a space, and ask a natural language question. The migration tool supports cross-workspace cloning by exporting the serialized space from one workspace and importing it into another with catalog remapping via string replacement.

The repository also contains a skill evaluation framework that tests agent behavior using controlled experiments (with-skill versus without-skill responses), binary MLflow judges for correctness and completeness, deterministic substring and regex assertions, and a prompt optimization loop. The Genie skill has baseline tests with eight test cases and a 100 percent pass rate.

---

## Adding Lab 6 to Automated Testing in Solutions

Lab 6 currently has no validation script in the solutions directory. Labs 2, 3, 4, and 7 each have corresponding scripts in `agent_modules/` that run as headless Databricks jobs via `submit.sh`. Lab 6 is the gap in the chain.

### What Lab 6 Produces

Lab 6 creates a Supervisor Agent that coordinates two agents: a Genie space (structured data queries over Delta Lake tables) and a Knowledge Assistant endpoint (unstructured document analysis). The output is a serving endpoint name that Lab 7 consumes. Today, Lab 6 is configured entirely through the Databricks UI, and validation is manual: run a few test queries in the chat interface and visually inspect the results.

### What a Validation Script Would Need to Verify

A `run_lab6.py` or `verify_lab6.py` script would need to confirm three things. First, that the MAS endpoint exists and is in a serving state. The Databricks SDK can query serving endpoint status directly. Second, that the endpoint responds to a natural language question that requires both agents. A question like "Find customers interested in renewable energy stocks and show me their current holdings" forces the supervisor to route to both the Genie agent (for holdings data) and the Knowledge Assistant (for interest data from profiles). Third, that the response contains substantive content from both data sources, not just one. This could be checked by looking for expected keywords or patterns in the response text (customer names that appear in the structured data, interest topics that appear only in the unstructured profiles).

### How It Fits the Existing Pattern

The existing scripts follow a consistent structure: parse command-line arguments for credentials, execute the lab's core logic, print PASS or FAIL for each check, and exit with code 0 or 1. A Lab 6 validation script would accept the same Neo4j and volume path arguments (even if it does not use them directly) plus the MAS endpoint name. It would use the Databricks SDK to query the MAS endpoint the same way `run_lab7.py` already does, but with simpler assertions focused on reachability and multi-agent routing rather than DSPy analysis.

The script would slot into the execution order between `run_lab4.py` and `run_lab7.py`. The `submit.sh` script already injects `MAS_ENDPOINT_NAME` from the `.env` file into every job, so no changes to the shell scripts would be required.

### UI Validation: verify_lab6.py

A `verify_lab6.py` script confirms the MAS endpoint is serving, sends a multi-agent query, and checks that the response draws from both agents. This is non-destructive, fast, and follows the `verify_lab2.py` pattern. It validates the outcome of the manual UI workflow in Lab 6 and slots into the execution order between `run_lab4.py` and `run_lab7.py`. No changes to `upload.sh`, `submit.sh`, or `clean.sh` would be needed. The `.env.example` and README already reference `MAS_ENDPOINT_NAME`.

---

## Automated End-to-End Pipeline

The UI validation script and the automated pipeline serve different purposes. The validation script checks that a human completed Lab 6 correctly. The automated pipeline creates the entire graph enrichment workflow from scratch, programmatically, so that evaluations can run against it without anyone touching the UI.

### Why This Matters

The existing solutions scripts already automate Labs 2 through 4 and Lab 7. The missing piece is Lab 5 (agent creation) and Lab 6 (Genie space, Knowledge Assistant, and Supervisor Agent). Once those are automated, the full chain runs end-to-end: data import, vector pipeline, Delta export, Genie and agent setup, MAS creation, and DSPy augmentation analysis. That complete chain becomes the foundation for running evaluations, measuring quality over time, testing changes to instructions or prompts, and comparing different configurations.

### What the Pipeline Needs to Create

The pipeline fills the gap between Lab 4 (Delta tables exist) and Lab 7 (MAS endpoint is queryable). Three resources need to be created programmatically.

**Genie Space.** The SDK's `w.genie.create_space` accepts a warehouse ID and a serialized space definition. The serialized space is a version-2 JSON string, and it can be constructed entirely from scratch without ever creating a space in the UI first. The minimum viable payload requires only a version number and at least one table identifier. Item-level `id` fields that appear in exported spaces (hex strings on sample questions, instructions, join specs) are auto-generated by the server when omitted; they are not required for creation.

The full format supports table references with optional descriptions, text instructions, example question-SQL pairs, UDF references, join specifications between tables, SQL snippets (filters, expressions, measures), sample questions, and benchmark question-answer pairs for evaluation. String values throughout the format use arrays of strings rather than plain strings, where each array element represents a line or segment.

All the information needed to construct the payload for this workshop already exists in the repository. The table names come from Lab 4's Delta export (accounts, banks, companies, customers, portfolio_holdings, stocks, transactions, plus the relationship tables). The text instructions come from Lab 6's README (the system instructions for identifying gaps, data quality issues, and cross-sell opportunities). Sample questions come from Lab 6's SAMPLE_QUERIES.md. Join specifications can be derived from the graph schema defined in Lab 2, since every relationship type maps to a join between its source and target node tables. The setup script would assemble these known values into the JSON structure and pass it to the SDK.

**Knowledge Assistant.** The Knowledge Assistant is a serving endpoint backed by a vector search index over the unstructured documents loaded in Lab 3. Creating it programmatically requires deploying an agent through the Databricks agents API, pointing it at the vector search index and configuring its retrieval and response behavior. The agent's endpoint name is needed as input to the MAS.

**Supervisor Agent.** The MAS coordinates the Genie space and the Knowledge Assistant. Creating it requires specifying both child agent endpoints, the system instructions (identifying gaps between customer interests and holdings, finding data quality issues, discovering cross-sell opportunities), and the supervisor's name and description. The MAS API returns a serving endpoint name that Lab 7's augmentation agent queries.

### Reusing the Existing Solutions Infrastructure

The automated pipeline should extend the existing solutions pattern rather than replacing it. The shell scripts, `.env` configuration, and job submission workflow all remain as they are. The pipeline adds new scripts to `agent_modules/` that handle the setup steps, and the existing `run_lab7.py` (and the augmentation agent package) run against the programmatically created MAS the same way they run against a manually created one.

The execution flow for the automated pipeline would look like this. First, run the existing data setup scripts: `run_lab2.py` imports graph data, `run_lab3.py` builds the vector pipeline, `run_lab4.py` exports Delta tables. Then run the new setup scripts: create the Genie space over the Delta tables, deploy the Knowledge Assistant over the vector index, and create the MAS that combines them. Finally, run the existing `run_lab7.py` against the new MAS endpoint. The only new `.env` variables would be whatever the setup scripts need beyond what already exists (warehouse ID for Genie, vector search index name for the Knowledge Assistant).

### Constructing the Genie Space From Known Inputs

No UI step or reference space export is needed. The serialized space definition can be assembled entirely from information already in the repository.

The version-2 JSON format has a straightforward structure. At the top level: a `version` field (set to 2), a `data_sources` object containing a `tables` array, an `instructions` object, a `config` object for sample questions, and an optional `benchmarks` object. Each table entry needs only its three-part Unity Catalog identifier (catalog.schema.table) and an optional description. Instructions are text blocks. Example question-SQL pairs map natural language questions to the SQL that answers them. Join specifications name two tables and the SQL condition that connects them.

The table identifiers are determined by Lab 4's Delta export, which writes seven node tables and seven relationship tables to Unity Catalog. The text instructions are the system prompt from Lab 6's README, telling the Genie to analyze customers, accounts, portfolios, and transactions. The sample questions are the test queries from Lab 6. Join specifications mirror the graph schema: customers connect to accounts via the HAS_ACCOUNT relationship table, accounts connect to portfolio holdings, holdings connect to stocks, and so on. Example question-SQL pairs can be written for the most common queries (total holdings by customer, transactions over a period, portfolio composition) to improve the Genie's SQL generation accuracy.

The setup script assembles these values into the JSON structure, serializes it to a string, and passes it to `w.genie.create_space` alongside the warehouse ID. The returned space ID is then used as input when creating the Supervisor Agent.

The Knowledge Assistant configuration and MAS system instructions follow the same principle. Both are already defined as specific text blocks in the Lab 5 and Lab 6 READMEs. The setup scripts use those same values directly.

### Running Evaluations

With the full pipeline automated, evaluations become a matter of running the chain and measuring outputs. The Genie API's beta evaluation endpoints allow defining benchmark questions in the space configuration and running eval runs that score the Genie's SQL generation against expected answers. The MAS endpoint can be queried with a fixed set of multi-agent questions and the responses compared against expected patterns or scored by an LLM judge. The DSPy augmentation agent's structured Pydantic output is already validated in `run_lab7.py`; extending that to track scores over time or compare across configurations is a natural next step.

The AI Dev Kit's evaluation framework provides a reference for how to structure this. Their pattern of controlled experiments (with and without a given configuration), binary judges, and deterministic assertions alongside LLM-based scoring maps well to evaluating the graph enrichment workflow. MLflow integration for tracking evaluation runs over time is another pattern worth adopting.

---

## Reference Links

- Genie REST API overview: docs.databricks.com/api/workspace/genie
- Create Space endpoint: docs.databricks.com/api/workspace/genie/createspace
- Conversation API guide: docs.databricks.com/aws/en/genie/conversation-api
- CLI genie commands: docs.databricks.com/aws/en/dev-tools/cli/reference/genie-commands
- Python SDK GenieAPI: databricks-sdk-py.readthedocs.io/en/latest/workspace/dashboards/genie.html
- AI Dev Kit Genie skill: github.com/databricks-solutions/ai-dev-kit/tree/main/databricks-skills/databricks-genie
