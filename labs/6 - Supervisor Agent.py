# Databricks notebook source

# MAGIC %md
# MAGIC # Supervisor Agent
# MAGIC
# MAGIC ### Estimated time: 10 minutes
# MAGIC
# MAGIC This lab combines the Genie and Knowledge Assistant from **5 - AI Agents** into a unified
# MAGIC Supervisor Agent that answers complex questions requiring both structured data and
# MAGIC unstructured document analysis.
# MAGIC
# MAGIC ### Prerequisites
# MAGIC
# MAGIC - Completed **5 - AI Agents** with both agents created:
# MAGIC   - Retail Investment Data Assistant (Genie)
# MAGIC   - graph-augmentation-knowledge-assistant (Knowledge Assistant)

# COMMAND ----------

# MAGIC %md
# MAGIC ## A. Create the Supervisor Agent
# MAGIC
# MAGIC 1. Navigate to the **Supervisor Agent** interface
# MAGIC 2. Click **Build** to create a new multi-agent system

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Add Agents
# MAGIC
# MAGIC Click **Configure Agents** to add your agents. You can select up to 20 different agents and tools.
# MAGIC
# MAGIC ### B1. Agent 1: Genie Space
# MAGIC
# MAGIC | Field | Value |
# MAGIC |-------|-------|
# MAGIC | **Type** | `Genie Space` |
# MAGIC | **Genie space** | Select your Retail Investment Genie |
# MAGIC | **Agent Name** | `agent-retail-investment-genie` |
# MAGIC | **Describe the content** | `Answers questions about retail investment customers, account balances, portfolio holdings, stock positions, banking relationships, and transaction history across structured data extracted from a graph database into Delta Lake tables.` |
# MAGIC
# MAGIC ### B2. Agent 2: Knowledge Assistant
# MAGIC
# MAGIC | Field | Value |
# MAGIC |-------|-------|
# MAGIC | **Type** | `Agent Endpoint` |
# MAGIC | **Agent Endpoint** | Select your Knowledge Assistant endpoint (e.g., `ka-6f0994b4-endpoint`) |
# MAGIC | **Agent Name** | `graph-augmentation-knowledge-assistant` |
# MAGIC | **Describe the content** | `This knowledge base contains comprehensive customer profiles, institutional data, and investment research documents for a retail investment platform. The content includes: CUSTOMER PROFILES: Detailed narratives containing demographics, risk profiles, current account holdings, investment preferences, personal financial goals, life circumstances, stated investment interests that may not yet be reflected in portfolios, savings habits, customer service preferences, credit scores, and banking relationship history.` |

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Configure System Settings
# MAGIC
# MAGIC | Field | Value |
# MAGIC |-------|-------|
# MAGIC | **Name** | `Retail Investment Intelligence System` |
# MAGIC
# MAGIC **Description**:
# MAGIC ```
# MAGIC Provides comprehensive retail investment intelligence by combining structured transactional
# MAGIC data analysis with unstructured customer insights and market research. Analyzes customer
# MAGIC portfolios, account activity, and holdings alongside qualitative preferences, investment
# MAGIC interests, and research recommendations to identify opportunities, gaps, and personalized
# MAGIC financial guidance.
# MAGIC ```
# MAGIC
# MAGIC **Instructions**:
# MAGIC ```
# MAGIC You are an intelligent investment analysis system. Use the Genie agent to query
# MAGIC structured data about customers, accounts, and portfolios. Use the Knowledge Assistant
# MAGIC to analyze customer profiles and documents. Your goal is to:
# MAGIC
# MAGIC 1. Identify gaps between customer interests (from profiles) and actual investments
# MAGIC 2. Find data quality issues where profile information isn't captured in structured data
# MAGIC 3. Discover cross-sell opportunities based on customer insights
# MAGIC 4. Provide comprehensive customer analysis combining both data sources
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Get the Endpoint Name
# MAGIC
# MAGIC After creating the Supervisor Agent, click the **cloud icon** in the top right corner
# MAGIC to view the endpoint details. Copy the endpoint name (e.g., `mas-01875d0e-endpoint`) —
# MAGIC you'll need this in **Lab 7**.

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Test Queries
# MAGIC
# MAGIC Basic tests to verify the system works:
# MAGIC ```
# MAGIC Find customers interested in renewable energy stocks and show me their current holdings
# MAGIC Which customers have risk profiles that don't match their portfolio composition?
# MAGIC What information exists in customer profiles that isn't captured in the structured database?
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Sample Queries by Use Case
# MAGIC
# MAGIC ### F1. Gap Analysis
# MAGIC Find mismatches between customer interests and their actual portfolios.
# MAGIC ```
# MAGIC Find customers who express interest in renewable energy in their profiles but don't have any renewable energy stocks
# MAGIC Which customers have expressed interest in ESG investing but don't have ESG funds in their portfolios?
# MAGIC Find customers who mentioned real estate investing in their profiles and show me their current investment positions
# MAGIC Are there any customers talking about technology stocks in their profiles who don't actually own any?
# MAGIC ```
# MAGIC
# MAGIC ### F2. Risk Profile Mismatch
# MAGIC Identify customers whose portfolios don't match their stated risk tolerance.
# MAGIC ```
# MAGIC Show me customers with aggressive risk profiles and analyze if their portfolios match their risk tolerance
# MAGIC Which conservative investors have portfolios that are too aggressive for their stated preferences?
# MAGIC Find mismatches between customer risk profiles in the database and their investment behavior
# MAGIC ```
# MAGIC
# MAGIC ### F3. Data Quality
# MAGIC Find information in profiles that's missing from structured data.
# MAGIC ```
# MAGIC What personal information appears in customer profile documents that isn't in the structured database?
# MAGIC Find data quality gaps between customer profiles and account records
# MAGIC Compare the structured customer data with profile narratives and identify missing fields
# MAGIC ```
# MAGIC
# MAGIC ### F4. Customer Intelligence
# MAGIC Get comprehensive views of individual customers.
# MAGIC ```
# MAGIC Tell me everything about customer C0001 - their accounts, holdings, transaction patterns, and personal preferences
# MAGIC What are the top investment interests mentioned across all customer profiles?
# MAGIC Show me customers in their 30s with high income and tell me about their investment strategies
# MAGIC ```
# MAGIC
# MAGIC ### F5. Portfolio Analysis
# MAGIC Analyze holdings and positions across customers.
# MAGIC ```
# MAGIC What are the most popular stocks held by customers and how are they performing?
# MAGIC Show me the total portfolio value for each customer and rank them
# MAGIC Which customers have the most diversified portfolios across different sectors?
# MAGIC What is the average portfolio size by customer risk profile?
# MAGIC ```
# MAGIC
# MAGIC ### F6. Transaction Activity
# MAGIC Examine account activity and patterns.
# MAGIC ```
# MAGIC Show me recent large transactions over $1000 and the accounts involved
# MAGIC Which customers have the most active trading patterns?
# MAGIC Find customers who frequently transfer money between accounts
# MAGIC ```
# MAGIC
# MAGIC ### F7. Market Research
# MAGIC Query investment research documents.
# MAGIC ```
# MAGIC What does the market research say about renewable energy investment opportunities?
# MAGIC Summarize the technology sector analysis and current trends
# MAGIC What investment strategies are recommended for moderate risk investors?
# MAGIC What are the key findings from the FinTech disruption report?
# MAGIC ```
# MAGIC
# MAGIC ### F8. Banking Relationships
# MAGIC Analyze customer-bank relationships.
# MAGIC ```
# MAGIC Which customers bank with First National Trust and what services do they use?
# MAGIC Compare the customer base across different banks
# MAGIC Show me customers with accounts at multiple banks
# MAGIC What is the total assets under management by bank?
# MAGIC ```
# MAGIC
# MAGIC ### F9. Cross-Sell Opportunities
# MAGIC Identify sales and service opportunities.
# MAGIC ```
# MAGIC Find customers interested in retirement planning who don't have sufficient retirement savings
# MAGIC Which high-income customers might be good candidates for wealth management services?
# MAGIC Show me customers with large cash balances who could benefit from investment accounts
# MAGIC ```
# MAGIC
# MAGIC ### F10. Compliance
# MAGIC Query regulatory and compliance information.
# MAGIC ```
# MAGIC What are the key compliance requirements for banks according to the regulatory documents?
# MAGIC Summarize the anti-money laundering regulations mentioned in the knowledge base
# MAGIC What capital requirements do banks need to maintain?
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## G. Advanced Multi-Agent Queries
# MAGIC
# MAGIC These sophisticated queries require coordination between both agents.
# MAGIC
# MAGIC ### Personalized Investment Discovery
# MAGIC ```
# MAGIC James Anderson has expressed interest in renewable energy stocks. What renewable energy
# MAGIC companies are mentioned in our research documents, and does he currently own any of them?
# MAGIC If not, which ones align with his moderate risk profile?
# MAGIC ```
# MAGIC *Combines: Customer profile + portfolio holdings + investment research + risk alignment*
# MAGIC
# MAGIC ```
# MAGIC Identify customers who have mentioned interest in real estate investing in their profiles.
# MAGIC Show me their current account balances and investment positions. Do any of them have
# MAGIC sufficient capital to pursue real estate investments based on the investment guide
# MAGIC recommendations?
# MAGIC ```
# MAGIC *Combines: Profile mining + account balances + positions + research recommendations*
# MAGIC
# MAGIC ```
# MAGIC Robert Chen is an aggressive investor interested in AI and autonomous vehicles. Based on
# MAGIC the technology sector analysis, what AI and autonomous vehicle stocks are discussed in our
# MAGIC research? Does Robert's current portfolio include these stocks, and what percentage of his
# MAGIC portfolio do they represent?
# MAGIC ```
# MAGIC *Combines: Customer preferences + research analysis + holdings + allocation calculations*
# MAGIC
# MAGIC ```
# MAGIC Maria Rodriguez has expressed interest in ESG and socially responsible investing. Identify
# MAGIC which companies in her current portfolio might not align with ESG principles, and suggest
# MAGIC alternative stocks from our research documents that would better match her values while
# MAGIC maintaining her conservative risk profile.
# MAGIC ```
# MAGIC *Combines: Customer values + portfolio analysis + ESG research + risk matching*
# MAGIC
# MAGIC ### Portfolio-Profile Alignment
# MAGIC ```
# MAGIC Find all customers with 'aggressive' risk profiles and analyze their actual portfolio
# MAGIC compositions. Cross-reference with their profile narratives about risk tolerance. Identify
# MAGIC any misalignments where portfolios are too conservative for stated preferences.
# MAGIC ```
# MAGIC *Combines: Structured risk data + portfolio holdings + unstructured risk narratives*
# MAGIC
# MAGIC ```
# MAGIC Which customers have mentioned specific investment interests (renewable energy, technology,
# MAGIC real estate, healthcare) in their profiles that are completely absent from their current
# MAGIC portfolio holdings? Rank by account balance to prioritize high-value opportunities.
# MAGIC ```
# MAGIC *Combines: Profile text analysis + portfolio gaps + account ranking*
# MAGIC
# MAGIC ```
# MAGIC Analyze the three customer profiles (James, Maria, Robert) and compare their stated
# MAGIC investment philosophies with their actual transaction patterns and portfolio compositions.
# MAGIC Highlight inconsistencies and opportunities for advisor outreach.
# MAGIC ```
# MAGIC *Combines: Profile analysis + transactions + portfolio composition + behavioral analysis*
# MAGIC
# MAGIC ### Research-Driven Targeting
# MAGIC ```
# MAGIC The renewable energy research document discusses Solar Energy Systems (SOEN) and Renewable
# MAGIC Power Inc (RPOW). Which customers in our database have expressed interest in solar or
# MAGIC renewable energy? Of those, who currently doesn't own these stocks and has sufficient
# MAGIC account balance to invest?
# MAGIC ```
# MAGIC *Combines: Research analysis + profile search + portfolio detection + balance filtering*
# MAGIC
# MAGIC ```
# MAGIC According to the technology sector analysis, AI and cybersecurity are key growth themes.
# MAGIC Identify customers working in technology fields (from their profiles) who might have
# MAGIC professional insight into these trends. Do their portfolios reflect this knowledge?
# MAGIC ```
# MAGIC *Combines: Profile occupation + research themes + portfolio positioning*
# MAGIC
# MAGIC ```
# MAGIC The real estate investment guide discusses crowdfunding platforms requiring $5,000-$10,000
# MAGIC minimum investments. Which customers have mentioned real estate interest in their profiles
# MAGIC and have checking or savings account balances exceeding $10,000 but no current real estate
# MAGIC exposure?
# MAGIC ```
# MAGIC *Combines: Research details + profile interests + balance analysis + portfolio gap*
# MAGIC
# MAGIC ### Life Stage Analysis
# MAGIC ```
# MAGIC Maria Rodriguez is a single mother planning for college expenses and retirement. Based on
# MAGIC her age, income from her profile, and current investment positions, is she on track to meet
# MAGIC the retirement planning strategies outlined in our research documents? What gaps exist?
# MAGIC ```
# MAGIC *Combines: Demographics + income + portfolio + retirement benchmarks*
# MAGIC
# MAGIC ```
# MAGIC Robert Chen aims to build a $5 million portfolio by age 40. Based on his current portfolio
# MAGIC value, age, and stated aggressive investment strategy, calculate his required annual return.
# MAGIC Is this realistic given the technology sector analysis and his current holdings?
# MAGIC ```
# MAGIC *Combines: Profile goals + portfolio value + demographics + sector expectations*
# MAGIC
# MAGIC ```
# MAGIC Identify customers in their 30s and 40s (peak earning years) who have mentioned retirement
# MAGIC planning in their profiles. Analyze their current investment account balances and compare
# MAGIC to the retirement planning strategy recommendations for their age group.
# MAGIC ```
# MAGIC *Combines: Age filtering + profile analysis + balance analysis + research benchmarks*
# MAGIC
# MAGIC ### Banking & Service Opportunities
# MAGIC ```
# MAGIC First National Trust and Pacific Coast Bank are profiled in our documents. Show me all
# MAGIC customers banking at these institutions, their total account balances, and cross-reference
# MAGIC their profiles for mentioned service preferences (digital vs. in-person). Are we delivering
# MAGIC services aligned with their preferences?
# MAGIC ```
# MAGIC *Combines: Bank relationships + account aggregation + profile preferences + institutional capabilities*
# MAGIC
# MAGIC ```
# MAGIC Which customers have accounts at multiple banks according to our structured data? Analyze
# MAGIC their profiles to understand why they maintain multiple relationships. Are there
# MAGIC consolidation opportunities or service gaps we need to address?
# MAGIC ```
# MAGIC *Combines: Multi-bank detection + profile analysis + service gap identification*
# MAGIC
# MAGIC ```
# MAGIC The bank profiles mention wealth management services. Identify high-net-worth customers
# MAGIC (based on total account balances and investment positions) who haven't been mentioned as
# MAGIC using wealth management services in their profiles. Calculate total assets under management
# MAGIC potential.
# MAGIC ```
# MAGIC *Combines: Net worth calculation + profile service analysis + opportunity sizing*
# MAGIC
# MAGIC ### Compliance Intelligence
# MAGIC ```
# MAGIC According to the regulatory compliance documents, what are the key AML (anti-money
# MAGIC laundering) monitoring requirements? Identify customers with transaction patterns showing
# MAGIC frequent large transfers between accounts. Cross-reference their profiles for legitimate
# MAGIC business reasons that might explain this activity.
# MAGIC ```
# MAGIC *Combines: Regulatory requirements + transaction patterns + profile context*
# MAGIC
# MAGIC ```
# MAGIC The compliance documents discuss customer suitability requirements. For each customer,
# MAGIC compare their stated risk profile in structured data with the risk tolerance narratives in
# MAGIC their profile documents. Flag any customers where documentation doesn't align and might
# MAGIC need updated suitability assessments.
# MAGIC ```
# MAGIC *Combines: Structured risk data + unstructured narratives + compliance matching*
# MAGIC
# MAGIC ### Sector & Market Timing
# MAGIC ```
# MAGIC The technology sector analysis mentions valuation concerns with median P/E of 29.4 vs.
# MAGIC historical 22.6. Identify customers heavily concentrated in technology stocks (>50% of
# MAGIC portfolio). Do their profiles indicate they understand these risks, or should advisors
# MAGIC reach out with rebalancing recommendations?
# MAGIC ```
# MAGIC *Combines: Sector concentration + valuation context + profile sophistication assessment*
# MAGIC
# MAGIC ```
# MAGIC Based on the market research documents, which investment themes are emerging (AI, renewable
# MAGIC energy, cybersecurity, etc.)? For each theme, identify the top 3 customers by account
# MAGIC balance who have expressed interest in these themes but have less than 10% portfolio
# MAGIC allocation to them.
# MAGIC ```
# MAGIC *Combines: Research themes + profile matching + allocation analysis + customer ranking*
# MAGIC
# MAGIC ### Comprehensive Reports
# MAGIC ```
# MAGIC Generate a complete financial intelligence report for customer C0001 (James Anderson)
# MAGIC including: all account balances and holdings, transaction patterns, stated investment
# MAGIC interests from his profile, gaps between interests and holdings, recommendations from
# MAGIC research documents that match his profile, and next best actions for his advisor.
# MAGIC ```
# MAGIC *Combines: Full structured profile + document analysis + gap analysis + research matching + recommendations*
# MAGIC
# MAGIC ```
# MAGIC Create a market opportunity dashboard showing: total customers by risk profile, top
# MAGIC investment interests mentioned across all profiles, current portfolio exposures by sector,
# MAGIC gaps between interests and holdings, and total addressable assets for each investment theme
# MAGIC from our research documents.
# MAGIC ```
# MAGIC *Combines: Customer segmentation + profile analysis + portfolio analytics + gap quantification + market sizing*

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC The Supervisor Agent is ready. Continue to **7 - Augmentation Agent** to use
# MAGIC the Supervisor Agent for analyzing documents and suggesting graph enrichments.
