# Sample Multi-Agent Queries

These queries demonstrate the power of combining structured data (Genie) with unstructured document analysis (Knowledge Assistant).

---

## Use Case Categories

### 1. Gap Analysis

Find mismatches between customer interests and their actual portfolios.

```
Find customers who express interest in renewable energy in their profiles but don't have any renewable energy stocks
Which customers have expressed interest in ESG investing but don't have ESG funds in their portfolios?
Find customers who mentioned real estate investing in their profiles and show me their current investment positions
Are there any customers talking about technology stocks in their profiles who don't actually own any?
```

### 2. Risk Profile Mismatch

Identify customers whose portfolios don't match their stated risk tolerance.

```
Show me customers with aggressive risk profiles and analyze if their portfolios match their risk tolerance
Which conservative investors have portfolios that are too aggressive for their stated preferences?
Find mismatches between customer risk profiles in the database and their investment behavior
```

### 3. Data Quality

Find information in profiles that's missing from structured data.

```
What personal information appears in customer profile documents that isn't in the structured database?
Find data quality gaps between customer profiles and account records
Compare the structured customer data with profile narratives and identify missing fields
```

### 4. Customer Intelligence

Get comprehensive views of individual customers.

```
Tell me everything about customer C0001 - their accounts, holdings, transaction patterns, and personal preferences
What are the top investment interests mentioned across all customer profiles?
Show me customers in their 30s with high income and tell me about their investment strategies
```

### 5. Portfolio Analysis

Analyze holdings and positions across customers.

```
What are the most popular stocks held by customers and how are they performing?
Show me the total portfolio value for each customer and rank them
Which customers have the most diversified portfolios across different sectors?
What is the average portfolio size by customer risk profile?
```

### 6. Transaction Activity

Examine account activity and patterns.

```
Show me recent large transactions over $1000 and the accounts involved
Which customers have the most active trading patterns?
Find customers who frequently transfer money between accounts
```

### 7. Market Research

Query investment research documents.

```
What does the market research say about renewable energy investment opportunities?
Summarize the technology sector analysis and current trends
What investment strategies are recommended for moderate risk investors?
What are the key findings from the FinTech disruption report?
```

### 8. Banking Relationships

Analyze customer-bank relationships.

```
Which customers bank with First National Trust and what services do they use?
Compare the customer base across different banks
Show me customers with accounts at multiple banks
What is the total assets under management by bank?
```

### 9. Cross-Sell Opportunities

Identify sales and service opportunities.

```
Find customers interested in retirement planning who don't have sufficient retirement savings
Which high-income customers might be good candidates for wealth management services?
Show me customers with large cash balances who could benefit from investment accounts
```

### 10. Compliance

Query regulatory and compliance information.

```
What are the key compliance requirements for banks according to the regulatory documents?
Summarize the anti-money laundering regulations mentioned in the knowledge base
What capital requirements do banks need to maintain?
```

---

## Advanced Multi-Agent Questions

These sophisticated queries require coordination between both agents.

### Personalized Investment Discovery

```
James Anderson has expressed interest in renewable energy stocks. What renewable energy companies are mentioned in our research documents, and does he currently own any of them? If not, which ones align with his moderate risk profile?
```
*Combines: Customer profile + portfolio holdings + investment research + risk alignment*

```
Identify customers who have mentioned interest in real estate investing in their profiles. Show me their current account balances and investment positions. Do any of them have sufficient capital to pursue real estate investments based on the investment guide recommendations?
```
*Combines: Profile mining + account balances + positions + research recommendations*

```
Robert Chen is an aggressive investor interested in AI and autonomous vehicles. Based on the technology sector analysis, what AI and autonomous vehicle stocks are discussed in our research? Does Robert's current portfolio include these stocks, and what percentage of his portfolio do they represent?
```
*Combines: Customer preferences + research analysis + holdings + allocation calculations*

```
Maria Rodriguez has expressed interest in ESG and socially responsible investing. Identify which companies in her current portfolio might not align with ESG principles, and suggest alternative stocks from our research documents that would better match her values while maintaining her conservative risk profile.
```
*Combines: Customer values + portfolio analysis + ESG research + risk matching*

### Portfolio-Profile Alignment

```
Find all customers with 'aggressive' risk profiles and analyze their actual portfolio compositions. Cross-reference with their profile narratives about risk tolerance. Identify any misalignments where portfolios are too conservative for stated preferences.
```
*Combines: Structured risk data + portfolio holdings + unstructured risk narratives*

```
Which customers have mentioned specific investment interests (renewable energy, technology, real estate, healthcare) in their profiles that are completely absent from their current portfolio holdings? Rank by account balance to prioritize high-value opportunities.
```
*Combines: Profile text analysis + portfolio gaps + account ranking*

```
Analyze the three customer profiles (James, Maria, Robert) and compare their stated investment philosophies with their actual transaction patterns and portfolio compositions. Highlight inconsistencies and opportunities for advisor outreach.
```
*Combines: Profile analysis + transactions + portfolio composition + behavioral analysis*

### Research-Driven Targeting

```
The renewable energy research document discusses Solar Energy Systems (SOEN) and Renewable Power Inc (RPOW). Which customers in our database have expressed interest in solar or renewable energy? Of those, who currently doesn't own these stocks and has sufficient account balance to invest?
```
*Combines: Research analysis + profile search + portfolio detection + balance filtering*

```
According to the technology sector analysis, AI and cybersecurity are key growth themes. Identify customers working in technology fields (from their profiles) who might have professional insight into these trends. Do their portfolios reflect this knowledge?
```
*Combines: Profile occupation + research themes + portfolio positioning*

```
The real estate investment guide discusses crowdfunding platforms requiring $5,000-$10,000 minimum investments. Which customers have mentioned real estate interest in their profiles and have checking or savings account balances exceeding $10,000 but no current real estate exposure?
```
*Combines: Research details + profile interests + balance analysis + portfolio gap*

### Life Stage Analysis

```
Maria Rodriguez is a single mother planning for college expenses and retirement. Based on her age, income from her profile, and current investment positions, is she on track to meet the retirement planning strategies outlined in our research documents? What gaps exist?
```
*Combines: Demographics + income + portfolio + retirement benchmarks*

```
Robert Chen aims to build a $5 million portfolio by age 40. Based on his current portfolio value, age, and stated aggressive investment strategy, calculate his required annual return. Is this realistic given the technology sector analysis and his current holdings?
```
*Combines: Profile goals + portfolio value + demographics + sector expectations*

```
Identify customers in their 30s and 40s (peak earning years) who have mentioned retirement planning in their profiles. Analyze their current investment account balances and compare to the retirement planning strategy recommendations for their age group.
```
*Combines: Age filtering + profile analysis + balance analysis + research benchmarks*

### Banking & Service Opportunities

```
First National Trust and Pacific Coast Bank are profiled in our documents. Show me all customers banking at these institutions, their total account balances, and cross-reference their profiles for mentioned service preferences (digital vs. in-person). Are we delivering services aligned with their preferences?
```
*Combines: Bank relationships + account aggregation + profile preferences + institutional capabilities*

```
Which customers have accounts at multiple banks according to our structured data? Analyze their profiles to understand why they maintain multiple relationships. Are there consolidation opportunities or service gaps we need to address?
```
*Combines: Multi-bank detection + profile analysis + service gap identification*

```
The bank profiles mention wealth management services. Identify high-net-worth customers (based on total account balances and investment positions) who haven't been mentioned as using wealth management services in their profiles. Calculate total assets under management potential.
```
*Combines: Net worth calculation + profile service analysis + opportunity sizing*

### Compliance Intelligence

```
According to the regulatory compliance documents, what are the key AML (anti-money laundering) monitoring requirements? Identify customers with transaction patterns showing frequent large transfers between accounts. Cross-reference their profiles for legitimate business reasons that might explain this activity.
```
*Combines: Regulatory requirements + transaction patterns + profile context*

```
The compliance documents discuss customer suitability requirements. For each customer, compare their stated risk profile in structured data with the risk tolerance narratives in their profile documents. Flag any customers where documentation doesn't align and might need updated suitability assessments.
```
*Combines: Structured risk data + unstructured narratives + compliance matching*

### Sector & Market Timing

```
The technology sector analysis mentions valuation concerns with median P/E of 29.4 vs. historical 22.6. Identify customers heavily concentrated in technology stocks (>50% of portfolio). Do their profiles indicate they understand these risks, or should advisors reach out with rebalancing recommendations?
```
*Combines: Sector concentration + valuation context + profile sophistication assessment*

```
Based on the market research documents, which investment themes are emerging (AI, renewable energy, cybersecurity, etc.)? For each theme, identify the top 3 customers by account balance who have expressed interest in these themes but have less than 10% portfolio allocation to them.
```
*Combines: Research themes + profile matching + allocation analysis + customer ranking*

### Comprehensive Reports

```
Generate a complete financial intelligence report for customer C0001 (James Anderson) including: all account balances and holdings, transaction patterns, stated investment interests from his profile, gaps between interests and holdings, recommendations from research documents that match his profile, and next best actions for his advisor.
```
*Combines: Full structured profile + document analysis + gap analysis + research matching + recommendations*

```
Create a market opportunity dashboard showing: total customers by risk profile, top investment interests mentioned across all profiles, current portfolio exposures by sector, gaps between interests and holdings, and total addressable assets for each investment theme from our research documents.
```
*Combines: Customer segmentation + profile analysis + portfolio analytics + gap quantification + market sizing*

---

These queries showcase insights that would be impossible with either structured or unstructured data alone.
