# Lab 5: Create AI Agents

This lab sets up Databricks AI/BI agents to query the lakehouse data using natural language.

## Prerequisites

- Completed [Lab 4](../lab_4_neo4j_to_lakehouse/README.md) to export graph data to Delta Lake tables
- Access to Databricks AI/BI workspace features

---

## Genie Agent (Structured Data)

The Genie agent queries structured lakehouse tables for customer accounts, portfolios, and transactions.

### Setup

1. Go to **AI/BI** → **Genie** → **Create Genie Space**

2. Configure:
   - **Name**: `Retail Investment Data Assistant`
   - **Description**: `Answers questions about retail investment customers, account balances, portfolio holdings, stock positions, banking relationships, and transaction history across structured data extracted from a graph database into Delta Lake tables.`
   - **Data Source**: Select your catalog and schema (e.g., `neo4j_demo.raw_data`)
   - **Tables**: Include all 14 tables (7 node + 7 relationship tables)

3. Click **Configure** to open the configuration panel, then go to the **Instructions** tab:

   **Text** (General Instructions):
   ```
   This data represents a retail investment platform with customers, accounts, portfolios, and transactions.
   - Customers can have multiple accounts at different banks
   - Positions represent stock holdings within accounts
   - Transactions flow between accounts (source performs, target benefits)
   - Use customer_id to join customer data across tables
   ```

   **SQL Expressions** - Click **+ Add** to define reusable business concepts:

   *Measures* (aggregated metrics):
   | Name | SQL Expression |
   |------|----------------|
   | Total Portfolio Value | `SUM(position.current_value)` |
   | Account Balance | `SUM(account.balance)` |
   | Customer Count | `COUNT(DISTINCT customer.customer_id)` |

   *Filters* (common WHERE conditions):
   | Name | SQL Expression |
   |------|----------------|
   | High Value Accounts | `account.balance > 100000` |
   | Recent Transactions | `transaction.transaction_date >= CURRENT_DATE - INTERVAL 30 DAYS` |

   *Dimensions* (grouping attributes):
   | Name | SQL Expression |
   |------|----------------|
   | Risk Category | `customer.risk_profile` |
   | Bank Name | `bank.name` |

4. Go to the **Data** tab to configure table metadata:
   - Add column descriptions for key fields
   - Add synonyms (e.g., "client" for "customer", "holdings" for "position")
   - Hide internal columns like `<id>` if they confuse users

5. Add sample questions using **+ Add a sample question** on the main Genie page

### Test Queries

```
Show me customers with investment accounts and their total portfolio values
What are the top 10 customers by account balance?
Show me all technology stock positions
Which customers have high risk profiles but conservative portfolios?
```

---

## Knowledge Assistant (Unstructured Data)

The Knowledge Assistant analyzes customer profiles and research documents from the Unity Catalog Volume.

### Setup

1. Go to **AI/BI** → **Agents** → **Create Agent** → **Knowledge Assistant**

2. **Basic Info**:
   - **Name**: `graph-augmentation-knowledge-assistant` (only letters, numbers, and dashes allowed)
   - **Description**: Copy the description text from below

3. **Configure Knowledge Sources**:
   - **Type**: Select `UC Files` from dropdown
   - **Source**: Click the folder icon and navigate to your volume:
     - **All catalogs** → **your_catalog** → **your_schema** → **source_files** → **html**
     - Example: `/Volumes/neo4j_augmentation_demo/raw_data/source_files/html`
   - **Name**: `investment-research-docs`
   - **Describe the content**: Copy the content description text from below

   The agent will index all HTML files in the directory:
   - Customer profiles (`customer_profile_*.html`)
   - Bank profiles (`bank_profile_*.html`, `bank_branch_*.html`)
   - Company research (`company_analysis_*.html`, `company_quarterly_report_*.html`)
   - Investment guides (`investment_strategy_*.html`, `real_estate_investment_guide.html`)
   - Market research (`market_analysis_*.html`, `renewable_energy_*.html`)
   - Industry insights (`retail_investment_disruption_*.html`, `regulatory_compliance_*.html`)

### Agent Description (paste into "Description" field)

```
This knowledge base contains comprehensive customer profiles, institutional data, and investment research documents for a retail investment platform. The content includes:

CUSTOMER PROFILES: Detailed narratives containing demographics, risk profiles, current account holdings, investment preferences, personal financial goals, life circumstances, stated investment interests that may not yet be reflected in portfolios, savings habits, customer service preferences, credit scores, and banking relationship history.

INSTITUTIONAL PROFILES: Bank and branch profiles describing organizational history, asset size, geographic presence, investment philosophy, service offerings, wealth management capabilities, business banking specialization, community involvement, and customer satisfaction metrics.

COMPANY RESEARCH: Investment analysis reports and quarterly earnings summaries covering business models, financial performance, market position, growth trajectories, competitive advantages, analyst ratings, and strategic initiatives.

INVESTMENT GUIDES: Strategy guides covering portfolio allocation approaches for different risk profiles, diversification principles, rebalancing strategies, tax efficiency techniques, retirement planning across life stages, and real estate investment opportunities including direct ownership, REITs, and alternative structures.

MARKET RESEARCH: Sector analysis covering technology trends, renewable energy opportunities, market valuations, growth drivers, competitive dynamics, and investment themes across various industries.

INDUSTRY INSIGHTS: Research on financial services industry transformation including digital banking, payment innovation, lending disruption, wealth management evolution, emerging technologies, regulatory compliance requirements, and competitive landscape changes.

Use this knowledge base to answer questions about customer investment interests and preferences, risk tolerance narratives, personal financial goals and life circumstances, banking relationship histories, institutional capabilities and specializations, company fundamentals and performance, investment strategy recommendations by risk profile, sector trends and opportunities, retirement planning approaches, real estate investing strategies, regulatory compliance requirements, and industry disruption.
```

### Knowledge Source Content Description (paste into "Describe the content" field)

```
HTML documents containing retail investment customer profiles with demographics, risk tolerance, investment preferences, and financial goals. Also includes bank and branch profiles, company analysis reports, quarterly earnings summaries, investment strategy guides for different risk profiles, market research on technology and renewable energy sectors, and industry insights on financial services transformation.
```

### Instructions in the Optional Field

```
You are analyzing unstructured customer profiles and investment research documents. Your primary objectives are to:

1. Extract detailed customer insights including stated investment interests, personal goals, risk tolerance narratives, family circumstances, and preferences that may not be reflected in their current portfolio holdings
2. Identify gaps between what customers express interest in (e.g., renewable energy, ESG investing, real estate) and their actual investment positions
3. Provide context about banking relationships, service preferences, and customer engagement patterns
4. Reference specific investment research and market trends from the knowledge base when relevant to customer interests
5. Highlight opportunities for portfolio alignment with customer values and stated preferences
6. Surface qualitative information about customer financial sophistication, life stage, and long-term objectives

When answering questions, cite specific details from customer profiles including customer IDs, ages, occupations, risk profiles, and direct references to their stated interests. Cross-reference market research documents when discussing investment opportunities related to customer interests.
```

### 4. Get Endpoint Name

After creating the Knowledge Assistant, click the **cloud icon** in the top right corner to view the endpoint details. Copy the endpoint name (e.g., `ka-6f0994b4-endpoint`) - you'll need this in Lab 6.

### Test Queries

```
What investment interests does James Anderson have that aren't reflected in his current portfolio?
Describe Maria Rodriguez's risk tolerance and family circumstances that influence her investment decisions
What are Robert Chen's long-term financial goals and how aggressive is his investment approach?
What renewable energy investment opportunities are discussed in the research documents?
Compare the investment philosophies of First National Trust and Pacific Coast Bank
```

---

## Next Steps

Continue to [Lab 6: Supervisor Agent](../lab_6_multi_agent/README.md) to combine both agents into a unified system.
