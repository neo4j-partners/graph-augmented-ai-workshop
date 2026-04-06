# Databricks notebook source

# MAGIC %md
# MAGIC # AI Agents
# MAGIC
# MAGIC ### Estimated time: 15-20 minutes
# MAGIC
# MAGIC This lab sets up two Databricks AI agents to query the lakehouse data using natural language:
# MAGIC
# MAGIC 1. **Genie Agent** — queries structured Delta Lake tables for customer accounts, portfolios, and transactions
# MAGIC 2. **Knowledge Assistant** — analyzes unstructured customer profiles and research documents from the Unity Catalog Volume
# MAGIC
# MAGIC ### Prerequisites
# MAGIC
# MAGIC - Completed **4 - Neo4j to Lakehouse** to export graph data to Delta Lake tables
# MAGIC - Access to Databricks AI/BI workspace features

# COMMAND ----------

# MAGIC %md
# MAGIC ## A. Genie Agent (Structured Data)
# MAGIC
# MAGIC The Genie agent queries structured lakehouse tables for customer accounts, portfolios, and transactions.
# MAGIC
# MAGIC ### A1. Create the Genie Space
# MAGIC
# MAGIC 1. Go to **AI/BI** > **Genie** > **Create Genie Space**
# MAGIC
# MAGIC 2. Configure:
# MAGIC    | Field | Value |
# MAGIC    |-------|-------|
# MAGIC    | **Name** | `Retail Investment Data Assistant` |
# MAGIC    | **Description** | `Answers questions about retail investment customers, account balances, portfolio holdings, stock positions, banking relationships, and transaction history across structured data extracted from a graph database into Delta Lake tables.` |
# MAGIC    | **Data Source** | Select your catalog and schema (e.g., `neo4j_workshop_<username>.raw_data`) |
# MAGIC    | **Tables** | Include all 14 tables (7 node + 7 relationship tables) |

# COMMAND ----------

# MAGIC %md
# MAGIC ### A2. Configure Instructions
# MAGIC
# MAGIC Click **Configure** to open the configuration panel, then go to the **Instructions** tab.
# MAGIC
# MAGIC **Text** (General Instructions):
# MAGIC ```
# MAGIC This data represents a retail investment platform with customers, accounts, portfolios, and transactions.
# MAGIC - Customers can have multiple accounts at different banks
# MAGIC - Positions represent stock holdings within accounts
# MAGIC - Transactions flow between accounts (source performs, target benefits)
# MAGIC - Use customer_id to join customer data across tables
# MAGIC ```
# MAGIC
# MAGIC **SQL Expressions** — Click **+ Add** to define reusable business concepts:
# MAGIC
# MAGIC *Measures* (aggregated metrics):
# MAGIC | Name | SQL Expression |
# MAGIC |------|----------------|
# MAGIC | Total Portfolio Value | `SUM(position.current_value)` |
# MAGIC | Account Balance | `SUM(account.balance)` |
# MAGIC | Customer Count | `COUNT(DISTINCT customer.customer_id)` |
# MAGIC
# MAGIC *Filters* (common WHERE conditions):
# MAGIC | Name | SQL Expression |
# MAGIC |------|----------------|
# MAGIC | High Value Accounts | `account.balance > 100000` |
# MAGIC | Recent Transactions | `transaction.transaction_date >= CURRENT_DATE - INTERVAL 30 DAYS` |
# MAGIC
# MAGIC *Dimensions* (grouping attributes):
# MAGIC | Name | SQL Expression |
# MAGIC |------|----------------|
# MAGIC | Risk Category | `customer.risk_profile` |
# MAGIC | Bank Name | `bank.name` |

# COMMAND ----------

# MAGIC %md
# MAGIC ### A3. Configure Table Metadata
# MAGIC
# MAGIC Go to the **Data** tab to configure table metadata:
# MAGIC - Add column descriptions for key fields
# MAGIC - Add synonyms (e.g., "client" for "customer", "holdings" for "position")
# MAGIC - Hide internal columns like `<id>` if they confuse users
# MAGIC
# MAGIC Add sample questions using **+ Add a sample question** on the main Genie page.

# COMMAND ----------

# MAGIC %md
# MAGIC ### A4. Test the Genie Agent
# MAGIC
# MAGIC Try these queries:
# MAGIC ```
# MAGIC Show me customers with investment accounts and their total portfolio values
# MAGIC What are the top 10 customers by account balance?
# MAGIC Show me all technology stock positions
# MAGIC Which customers have high risk profiles but conservative portfolios?
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Knowledge Assistant (Unstructured Data)
# MAGIC
# MAGIC The Knowledge Assistant analyzes customer profiles and research documents from the Unity Catalog Volume.
# MAGIC
# MAGIC ### B1. Create the Knowledge Assistant
# MAGIC
# MAGIC 1. Go to **AI/BI** > **Agents** > **Create Agent** > **Knowledge Assistant**
# MAGIC
# MAGIC 2. **Basic Info**:
# MAGIC    | Field | Value |
# MAGIC    |-------|-------|
# MAGIC    | **Name** | `graph-augmentation-knowledge-assistant` |
# MAGIC    | **Description** | See the description text in step B2 below |

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Agent Description
# MAGIC
# MAGIC Paste this into the **Description** field:
# MAGIC
# MAGIC ```
# MAGIC This knowledge base contains comprehensive customer profiles, institutional data, and
# MAGIC investment research documents for a retail investment platform. The content includes:
# MAGIC
# MAGIC CUSTOMER PROFILES: Detailed narratives containing demographics, risk profiles, current
# MAGIC account holdings, investment preferences, personal financial goals, life circumstances,
# MAGIC stated investment interests that may not yet be reflected in portfolios, savings habits,
# MAGIC customer service preferences, credit scores, and banking relationship history.
# MAGIC
# MAGIC INSTITUTIONAL PROFILES: Bank and branch profiles describing organizational history, asset
# MAGIC size, geographic presence, investment philosophy, service offerings, wealth management
# MAGIC capabilities, business banking specialization, community involvement, and customer
# MAGIC satisfaction metrics.
# MAGIC
# MAGIC COMPANY RESEARCH: Investment analysis reports and quarterly earnings summaries covering
# MAGIC business models, financial performance, market position, growth trajectories, competitive
# MAGIC advantages, analyst ratings, and strategic initiatives.
# MAGIC
# MAGIC INVESTMENT GUIDES: Strategy guides covering portfolio allocation approaches for different
# MAGIC risk profiles, diversification principles, rebalancing strategies, tax efficiency techniques,
# MAGIC retirement planning across life stages, and real estate investment opportunities including
# MAGIC direct ownership, REITs, and alternative structures.
# MAGIC
# MAGIC MARKET RESEARCH: Sector analysis covering technology trends, renewable energy opportunities,
# MAGIC market valuations, growth drivers, competitive dynamics, and investment themes across
# MAGIC various industries.
# MAGIC
# MAGIC INDUSTRY INSIGHTS: Research on financial services industry transformation including digital
# MAGIC banking, payment innovation, lending disruption, wealth management evolution, emerging
# MAGIC technologies, regulatory compliance requirements, and competitive landscape changes.
# MAGIC
# MAGIC Use this knowledge base to answer questions about customer investment interests and
# MAGIC preferences, risk tolerance narratives, personal financial goals and life circumstances,
# MAGIC banking relationship histories, institutional capabilities and specializations, company
# MAGIC fundamentals and performance, investment strategy recommendations by risk profile, sector
# MAGIC trends and opportunities, retirement planning approaches, real estate investing strategies,
# MAGIC regulatory compliance requirements, and industry disruption.
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ### B3. Configure Knowledge Sources
# MAGIC
# MAGIC | Field | Value |
# MAGIC |-------|-------|
# MAGIC | **Type** | `UC Files` |
# MAGIC | **Source** | Navigate to your volume: **All catalogs** > **your_catalog** > **your_schema** > **source_files** > **html** (e.g., `/Volumes/neo4j_workshop_<username>/raw_data/source_files/html`) |
# MAGIC | **Name** | `investment-research-docs` |
# MAGIC | **Describe the content** | See the content description below |
# MAGIC
# MAGIC **Content Description** (paste into "Describe the content" field):
# MAGIC ```
# MAGIC HTML documents containing retail investment customer profiles with demographics, risk
# MAGIC tolerance, investment preferences, and financial goals. Also includes bank and branch
# MAGIC profiles, company analysis reports, quarterly earnings summaries, investment strategy
# MAGIC guides for different risk profiles, market research on technology and renewable energy
# MAGIC sectors, and industry insights on financial services transformation.
# MAGIC ```
# MAGIC
# MAGIC The agent will index all HTML files in the directory:
# MAGIC - Customer profiles (`customer_profile_*.html`)
# MAGIC - Bank profiles (`bank_profile_*.html`, `bank_branch_*.html`)
# MAGIC - Company research (`company_analysis_*.html`, `company_quarterly_report_*.html`)
# MAGIC - Investment guides (`investment_strategy_*.html`, `real_estate_investment_guide.html`)
# MAGIC - Market research (`market_analysis_*.html`, `renewable_energy_*.html`)
# MAGIC - Industry insights (`retail_investment_disruption_*.html`, `regulatory_compliance_*.html`)

# COMMAND ----------

# MAGIC %md
# MAGIC ### B4. Add Instructions
# MAGIC
# MAGIC Paste this into the **Instructions** field:
# MAGIC
# MAGIC ```
# MAGIC You are analyzing unstructured customer profiles and investment research documents. Your
# MAGIC primary objectives are to:
# MAGIC
# MAGIC 1. Extract detailed customer insights including stated investment interests, personal goals,
# MAGIC    risk tolerance narratives, family circumstances, and preferences that may not be reflected
# MAGIC    in their current portfolio holdings
# MAGIC 2. Identify gaps between what customers express interest in (e.g., renewable energy, ESG
# MAGIC    investing, real estate) and their actual investment positions
# MAGIC 3. Provide context about banking relationships, service preferences, and customer engagement
# MAGIC    patterns
# MAGIC 4. Reference specific investment research and market trends from the knowledge base when
# MAGIC    relevant to customer interests
# MAGIC 5. Highlight opportunities for portfolio alignment with customer values and stated preferences
# MAGIC 6. Surface qualitative information about customer financial sophistication, life stage, and
# MAGIC    long-term objectives
# MAGIC
# MAGIC When answering questions, cite specific details from customer profiles including customer IDs,
# MAGIC ages, occupations, risk profiles, and direct references to their stated interests.
# MAGIC Cross-reference market research documents when discussing investment opportunities related to
# MAGIC customer interests.
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ### B5. Get the Endpoint Name
# MAGIC
# MAGIC After creating the Knowledge Assistant, click the **cloud icon** in the top right corner
# MAGIC to view the endpoint details. Copy the endpoint name (e.g., `ka-6f0994b4-endpoint`) —
# MAGIC you'll need this in **6 - Supervisor Agent**.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B6. Test the Knowledge Assistant
# MAGIC
# MAGIC Try these queries:
# MAGIC ```
# MAGIC What investment interests does James Anderson have that aren't reflected in his current portfolio?
# MAGIC Describe Maria Rodriguez's risk tolerance and family circumstances that influence her investment decisions
# MAGIC What are Robert Chen's long-term financial goals and how aggressive is his investment approach?
# MAGIC What renewable energy investment opportunities are discussed in the research documents?
# MAGIC Compare the investment philosophies of First National Trust and Pacific Coast Bank
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC Both agents are ready. Continue to **6 - Supervisor Agent** to combine them into a
# MAGIC unified system that answers complex questions requiring both structured data and
# MAGIC unstructured document analysis.
