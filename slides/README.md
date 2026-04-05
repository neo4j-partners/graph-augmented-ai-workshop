# Workshop Slides

Presentation slides for the Neo4j + Databricks Integration Workshop. All slides use [Marp](https://marp.app/) markdown format.

## Presentations

| Lab | Slides | Description |
|-----|--------|-------------|
| **Background** | [00-background-slides.md](./00-background-slides.md) | Introduction: Facts vs Intent, the enrichment loop |
| **Setup** | [01-lab1-databricks-upload-slides.md](./01-lab1-databricks-upload-slides.md) | Setup: Upload CSV and HTML data to Unity Catalog |
| **Import** | [02-lab2-neo4j-import-slides.md](./02-lab2-neo4j-import-slides.md) | Import: Load data into Neo4j using Spark Connector |
| **Lab 4** | [04-lab4-export-to-lakehouse-slides.md](./04-lab4-export-to-lakehouse-slides.md) | Export graph data back to Delta tables |
| **Lab 5** | [05-lab5-ai-agents-slides.md](./05-lab5-ai-agents-slides.md) | Create Genie and Knowledge Assistants |
| **Lab 6** | [06-lab6-multi-agent-slides.md](./06-lab6-multi-agent-slides.md) | Build Supervisor Agent system |
| **Lab 7** | [07-lab7-augmentation-agent-slides.md](./07-lab7-augmentation-agent-slides.md) | AI-driven graph augmentation analysis |

## How to Present

### Option 1: Marp CLI

```bash
# Install Marp
npm install -g @marp-team/marp-cli

# Present slides
marp 01-lab1-databricks-upload-slides.md --server

# Export to PDF
marp 01-lab1-databricks-upload-slides.md --pdf

# Export all to PDF
for file in *.md; do marp "$file" --pdf; done
```

### Option 2: VS Code Extension

1. Install [Marp for VS Code](https://marketplace.visualstudio.com/items?itemName=marp-team.marp-vscode)
2. Open any slide file
3. Press `Cmd+K V` to preview
4. Use the export button for PDF/HTML

### Option 3: Marp Web

1. Visit [web.marp.app](https://web.marp.app/)
2. Paste slide content
3. Present directly in browser

## Workshop Flow

```
Lab 1: Data Upload
       ↓
Lab 2: Neo4j Import (Spark Connector)
       ↓
Lab 3: (Reserved for future lab)
       ↓
Lab 4: Export to Lakehouse
       ↓
Lab 5: Create AI Agents (Genie + Knowledge)
       ↓
Lab 6: Supervisor Agent
       ↓
Lab 7: Graph Augmentation Analysis
```

## Slide Count

- **Total Presentations:** 6
- **Total Slides:** ~18 slides
- **Format:** Marp Markdown
