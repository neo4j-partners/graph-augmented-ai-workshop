# Extracting Entities from Unstructured Text to Enrich the Financial Graph

The financial graph in this demo knows that James Anderson holds positions in TechCore Solutions and Semiconductor Tech. It knows his account balances, his credit score, his risk profile. What it cannot answer is that James Anderson is interested in renewable energy stocks, that he works as a senior software engineer, or that he considers himself a moderate-risk investor saving for retirement. That information lives in HTML customer profiles, investment research documents, and compliance reports sitting in the Databricks volume. The graph cannot see any of it.

Lab 7 addresses part of this gap. Its DSPy-based augmentation agent reads the unstructured documents, identifies missing entity types, attributes, and relationships, and outputs structured suggestions. But the pipeline stops at suggestion. The output is a list of proposals for a human to review. No entities are extracted from the text. No new nodes or relationships are written to the graph. The gap between "we know what's missing" and "the graph now contains it" remains open.

The agent-memory library has an extraction pipeline built for exactly this class of problem. It takes unstructured text, runs it through configurable extractors, validates and deduplicates the results against what already exists in the graph, and writes structured entities with typed relationships. This document describes, at a high level, how that pipeline could close the loop that Lab 7 leaves open.

## What the Extraction Pipeline Does

The agent-memory extraction pipeline is a four-stage process that converts unstructured text into graph-ready entities. Each stage has a specific job, and the stages run in sequence because each one depends on the output of the one before it.

```
                    Unstructured Text
                    (HTML profiles, research docs,
                     compliance reports)
                          |
                          v
              +-----------------------+
              |     EXTRACTION        |
              |                       |
              |  Read the text and    |
              |  identify entities:   |
              |  people, companies,   |
              |  locations, themes,   |
              |  financial concepts   |
              +-----------+-----------+
                          |
                  extracted entities
                  (name, type, confidence)
                          |
                          v
              +-----------------------+
              |     VALIDATION        |
              |                       |
              |  Filter out noise:    |
              |  stopwords, too-short |
              |  names, punctuation,  |
              |  numeric-only strings |
              +-----------+-----------+
                          |
                  valid entities only
                          |
                          v
              +-----------------------+
              |  ENTITY RESOLUTION    |
              |                       |
              |  Match against the    |
              |  existing graph:      |
              |  exact match, fuzzy   |
              |  match, embedding     |
              |  similarity           |
              |                       |
              |  Merge duplicates,    |
              |  flag near-matches    |
              +-----------+-----------+
                          |
                  deduplicated entities
                  with merge decisions
                          |
                          v
              +-----------------------+
              |     GRAPH WRITE       |
              |                       |
              |  Create new nodes     |
              |  and relationships    |
              |  in Neo4j, or merge   |
              |  properties into      |
              |  existing nodes       |
              +-----------------------+
```

**Extraction** is where the text gets read. The pipeline supports three extractors. A statistical NER model (spaCy) that runs fast and catches standard entity types like people, organizations, and locations. A zero-shot model (GLiNER) that can recognize domain-specific entity types without training data. And an LLM-based extractor that handles the hardest cases: coreference resolution (knowing that "he" refers to James Anderson), implicit entities (inferring "retirement savings goal" from a sentence about long-term planning), and relationship extraction (connecting an interest to a person). Each extractor produces the same output format, so downstream stages do not care which one ran.

**Validation** filters noise. Named entity recognition is imprecise. It flags common words as entities, extracts fragments of sentences, and sometimes identifies punctuation as a name. The validation stage applies a set of rules: reject stopwords, reject names shorter than two characters, reject purely numeric strings. This is a quality gate that prevents garbage from reaching the graph.

**Entity resolution** is the stage that makes the pipeline aware of what the graph already contains. When extraction pulls "TechCore Solutions" from a customer profile, resolution checks whether a Company node with that name already exists. It uses three strategies in order of confidence: exact string match, fuzzy string match (for typos and abbreviations), and embedding similarity (for semantically equivalent names that look different on the surface). Entities that match above a high threshold are merged automatically. Entities that match above a lower threshold are flagged for review. Everything else is treated as new.

**Graph write** creates the nodes and relationships. New entities become new nodes with labels derived from their type. Entities that matched existing nodes get their properties merged rather than duplicated. Relationships between entities (extracted by the LLM extractor or inferred from document co-occurrence) become typed edges in the graph.

## How It Applies to the Financial Graph

The financial graph has seven node types: Customer, Account, Bank, Transaction, Position, Stock, and Company. The unstructured documents mention concepts that cut across and extend this schema.

Consider what lives in the HTML customer profiles alone. Investment interests (renewable energy, retail companies, technology sector). Employment details (job titles, employers). Financial goals (retirement savings, college fund, wealth preservation). Life circumstances (family status, career stage, geographic preferences). None of these have nodes in the graph. They exist only as sentences in documents that the graph cannot traverse.

The extraction pipeline would process these documents and produce entities that fall into two categories.

**Entities that match existing nodes.** When a customer profile mentions "TechCore Solutions," the pipeline resolves that against the existing Company node. When it mentions "James Anderson," it resolves against the existing Customer node. These matches do not create new nodes. They create relationships between the existing nodes and the new entities extracted from the same document, or they add properties to existing nodes that the structured CSV data did not contain.

**Entities that require new node types.** Investment themes like "renewable energy" or "fintech" have no home in the current schema. Financial goals like "retirement savings" or "college fund" are not represented. The extraction pipeline would create these as new nodes with new labels, then connect them to the Customer nodes they were extracted alongside.

```
    BEFORE: What the graph knows about James Anderson

    (James Anderson)---[:HAS_ACCOUNT]--->(Checking A00001)
         |                                     |
         +-----[:HAS_ACCOUNT]--->(Savings A00002)
                                       |
                                [:HAS_POSITION]
                                       |
                                       v
                              (Position: 150 shares)
                                       |
                                 [:OF_SECURITY]
                                       |
                                       v
                              (Stock: TCOR TechCore Solutions)
                                       |
                                  [:OF_COMPANY]
                                       |
                                       v
                              (Company: TechCore Solutions)


    AFTER: What the graph knows after extraction from
           James Anderson's HTML profile

    (James Anderson)---[:HAS_ACCOUNT]--->(Checking A00001)
         |                                     |
         +-----[:HAS_ACCOUNT]--->(Savings A00002)
         |                               |
         |                         [:HAS_POSITION]
         |                               |
         |                               v
         |                      (Position: 150 shares)
         |                               |
         |                         [:OF_SECURITY]
         |                               |
         |                               v
         |                      (Stock: TCOR TechCore Solutions)
         |                               |
         |                          [:OF_COMPANY]
         |                               |
         |                               v
         |                      (Company: TechCore Solutions)
         |
         +---[:INTERESTED_IN]--->(Theme: Renewable Energy)
         |
         +---[:INTERESTED_IN]--->(Theme: Retail Investment)
         |
         +---[:HAS_GOAL]------->(Goal: Retirement Savings)
         |
         +---[:EMPLOYED_AT]---->(Employer: Tech Company)
```

The bottom half of the "after" diagram is entirely new. Those nodes and relationships did not exist in the structured CSV data. They were extracted from the unstructured HTML profile by the pipeline.

## How Lab 7 and the Extraction Pipeline Fit Together

Lab 7 and the extraction pipeline are not competitors. They solve different halves of the same problem.

Lab 7 answers the question: what is missing from the graph? It compares structured data against unstructured documents and identifies gaps. Its output is a list of suggested node types, attributes, and relationships that would make the graph more complete. This is a schema-level analysis. It tells you that the graph needs an InvestmentTheme node type, that Customer nodes should have a lifeStage property, and that an INTERESTED_IN relationship should connect customers to themes.

The extraction pipeline answers the question: what specific entities exist in the text, and how do they connect to what the graph already has? Its output is concrete nodes and relationships ready to write. It tells you that James Anderson is interested in renewable energy, that Sarah Chen has a goal of wealth preservation, and that the compliance document references Basel III capital requirements.

The two fit together as a design-then-build sequence.

```
    Unstructured Documents
    (HTML profiles, research,
     compliance reports)
              |
              v
    +-------------------+
    |  LAB 7            |
    |  DSPy Analysis    |      "The graph needs InvestmentTheme
    |                   | ---->  nodes, INTERESTED_IN relationships,
    |  Schema-level     |        and a lifeStage property on Customer."
    |  gap detection    |
    +-------------------+
              |
              | schema decisions feed into
              | ontology configuration
              v
    +-------------------+
    |  ONTOLOGY CONFIG  |
    |                   |      Define entity types, subtypes,
    |  What types are   |      relationship constraints, and
    |  valid? What      |      validation rules that match the
    |  relationships    |      schema decisions from Lab 7.
    |  are allowed?     |
    +-------------------+
              |
              | configured ontology guides
              | extraction behavior
              v
    +-------------------+
    |  EXTRACTION       |
    |  PIPELINE         |      Process every HTML document.
    |                   |      Extract entities typed against
    |  Entity-level     |      the ontology. Resolve against
    |  population       |      existing graph. Write new nodes
    |                   |      and relationships.
    +-------------------+
              |
              v
    Financial Graph
    (enriched with entities
     from unstructured text)
```

Lab 7 runs first, infrequently, when the team wants to assess what the graph is missing. Its output informs how the ontology is configured: what entity types to recognize, what relationship types to allow, what subtypes to distinguish. The extraction pipeline runs afterward, potentially on a schedule, processing documents against that configured ontology and populating the graph with concrete entities.

## What the Ontology Does Here

The extraction pipeline does not just pull every noun out of every document and throw it into the graph. It extracts entities according to a configurable type system called an ontology. The ontology defines what kinds of things the pipeline should look for, what relationships are valid between them, and what properties each type carries.

For the financial graph, the ontology would be configured with types that extend the existing schema. The structured graph already has Customer, Company, Stock, and the rest. The ontology adds the types that Lab 7 identified as missing.

```
    Ontology for the Financial Graph

    Existing types             New types from Lab 7
    (already in the graph)     (to be extracted from text)
    ----------------------     --------------------------
    CUSTOMER                   INVESTMENT_THEME
    COMPANY                    FINANCIAL_GOAL
    STOCK                      EMPLOYER
    ACCOUNT                    REGULATORY_FRAMEWORK
    BANK                       MARKET_SECTOR
    TRANSACTION                LIFE_CIRCUMSTANCE
    POSITION

    Relationship constraints
    --------------------------
    CUSTOMER  ---[:INTERESTED_IN]--->  INVESTMENT_THEME
    CUSTOMER  ---[:HAS_GOAL]-------->  FINANCIAL_GOAL
    CUSTOMER  ---[:EMPLOYED_AT]----->  EMPLOYER
    EMPLOYER  ---[:IN_SECTOR]------->  MARKET_SECTOR
    STOCK     ---[:IN_THEME]-------->  INVESTMENT_THEME
    COMPANY   ---[:SUBJECT_TO]------>  REGULATORY_FRAMEWORK
```

The ontology constrains extraction so the pipeline does not create nonsense relationships or invent types that have no meaning in the financial domain. When the LLM extractor reads "interested in renewable energy," the ontology tells it that "renewable energy" should be typed as INVESTMENT_THEME, not COMPANY or LOCATION. When it reads "works at a tech company," the ontology tells it that the employer is typed as EMPLOYER, not STOCK.

The ontology is loaded from a configuration file, not hardcoded. A different deployment of the same pipeline with a different ontology would extract different entity types from the same documents.

## Where Entity Resolution Earns Its Keep

The financial graph has 102 Company nodes and 102 Stock nodes loaded from structured CSV data. The HTML documents mention many of the same companies and stocks by name. Without entity resolution, the pipeline would create duplicate nodes for every company mentioned in a document, producing a graph with two or three nodes for TechCore Solutions that should be one.

Entity resolution prevents this. When the pipeline extracts "TechCore Solutions" from a customer profile, it checks the existing graph before writing anything.

```
    Extracted from text:  "TechCore Solutions"
                               |
                               v
                    +---------------------+
                    | EXACT MATCH         |
                    | Compare against     |
                    | existing Company    |
                    | and Stock nodes     |
                    +----------+----------+
                               |
                      match found: Company node
                      with name "TechCore Solutions"
                               |
                               v
                    +---------------------+
                    | MERGE, NOT CREATE   |
                    |                     |
                    | Do not create a new |
                    | node. Instead, link |
                    | the INTERESTED_IN   |
                    | relationship to the |
                    | existing Company    |
                    | node.               |
                    +---------------------+
```

The harder cases are where entities in the text do not exactly match what is in the graph. A document might reference "TechCore" instead of "TechCore Solutions," or "Semiconductor Technologies" instead of "Semiconductor Tech." Fuzzy matching catches abbreviations and minor variations. Embedding similarity catches semantically equivalent names that look different on the surface.

The resolution stage also respects entity types. A person named "Amazon" (unlikely but possible in the data) and the company named "Amazon" would not be merged, because the ontology types them differently and resolution compares entities of the same type only.

## The Full Pipeline in Context of the Demo

Placing the extraction pipeline into the existing lab sequence, it sits between the current Lab 7 (gap analysis) and what would be a new step: writing the extracted entities back to Neo4j and then exporting the enriched graph back to Delta Lake tables for the Genie agent to query.

```
    Lab 1: Upload CSVs and HTML to Databricks
              |
    Lab 2: Import structured CSV data into Neo4j
              |          (764 nodes, 814 relationships)
              |
    Lab 3: Embed HTML documents as vectors in Neo4j
              |          (Document and Chunk nodes)
              |
    Lab 4: Export graph to Delta Lake tables
              |
    Labs 5-6: AI agents query both stores
              |
              v
    Lab 7: DSPy agent identifies schema gaps
              |
              |   "The graph needs InvestmentTheme nodes,
              |    INTERESTED_IN relationships, ..."
              |
              v
    NEW: Configure ontology from Lab 7 output
              |
              v
    NEW: Run extraction pipeline over HTML documents
              |
              |   Extract entities, validate, resolve
              |   against existing graph, write new
              |   nodes and relationships
              |
              v
    NEW: Re-export enriched graph to Delta Lake
              |
              v
    Labs 5-6 again: AI agents now see the new entities
              |
              |   Genie can answer "which customers are
              |   interested in renewable energy?" because
              |   INTERESTED_IN relationships now exist
              |   as queryable structure.
              |
              v
    Lab 7 again: DSPy agent finds smaller gaps
              |
              |   The obvious gaps are filled. Now it
              |   finds subtler ones: implied risk
              |   preferences, cross-customer patterns,
              |   regulatory exposure chains.
```

The pipeline turns the demo from a one-shot analysis ("here is what's missing") into a loop ("extract what's missing, then look again"). Each pass through the loop enriches the graph, which gives the AI agents more structure to query, which surfaces more nuanced gaps on the next pass.

## What This Costs

**Extraction quality depends on the extractor.** The statistical NER model (spaCy) is fast but limited to standard entity types. It will catch company names and locations but miss investment themes and financial goals. The LLM extractor handles those domain-specific types but is slower and more expensive per document. For 14 HTML documents, the cost is trivial. For thousands of documents in a production deployment, the choice of extractor has real cost and latency implications.

**The ontology requires upfront design.** Someone has to decide what entity types to extract, what relationships to allow, and what subtypes to distinguish. Lab 7 provides a starting point, but its suggestions are proposals, not a finished schema. Translating "the graph probably needs an InvestmentTheme node type" into a configured ontology with subtypes, attributes, and relationship constraints requires domain judgment.

**Entity resolution is imperfect.** Fuzzy matching and embedding similarity reduce duplicates but do not eliminate them. An entity that falls just below the merge threshold creates a duplicate node. An entity that falls just above it merges two things that should have been separate. The thresholds need tuning for the financial domain, and the results need periodic review.

**The enriched graph changes what the agents see.** Adding hundreds of new relationships changes query results. The Genie agent, querying Delta Lake tables, will see new rows in new tables. The Knowledge Agent, searching vectors, will find new connections. These changes need to be validated before the enriched graph is treated as authoritative, especially in a financial services context where incorrect entity linking could associate a customer with the wrong investment theme or a company with the wrong regulatory framework.

The extraction pipeline does not replace human judgment about what belongs in the graph. It automates the mechanical work of reading documents, identifying entities, and proposing graph writes. The ontology configuration and the resolution thresholds are where domain expertise enters the system. The pipeline handles volume. The humans handle correctness.
