# Massy Supply Chain Intelligence Agent

> An agentic AI system built for Massy Group's Caribbean distribution network —
> spanning Trinidad, Tobago, Barbados, Guyana, and St. Lucia.

Built by **Sebastien Ghent** — MS Computer Science, University of South Florida (4.0 GPA)

---

## What this is

A supply chain intelligence agent that an operations manager can query in plain English.
The agent autonomously decides which tools to call, chains them in the right order,
and returns structured, quantified recommendations.

**Example:**
> *"What should we reorder for Port of Spain this week and what's the most efficient route to restock?"*

The agent checks inventory, runs demand forecasting, optimises the delivery route,
and reports the carbon cost — all from a single query.

---

## Architecture

```
Streamlit UI (localhost:8501)
        │
        ▼
MassyAgent — OpenAI gpt-4o-mini
  function calling · max 8 tool steps
        │
        ▼
7 Python tools (boto3 → AWS DynamoDB)
        │
        ▼
AWS Data Layer
  DynamoDB: inventory · orders · locations
  S3: data lake · static landing page
  IAM: scoped roles · read-only reviewer account
  Terraform: all infrastructure as code
```

---

## The 7 Tools

| # | Tool | Algorithm | What it answers |
|---|------|-----------|----------------|
| 1 | `get_inventory_status` | DynamoDB query + reorder logic | What's low on stock right now? |
| 2 | `get_demand_forecast` | FP-Growth basket analysis + Markov chain | What will we need and when? |
| 3 | `optimize_warehouse` | 0-1 Knapsack (dynamic programming) | What's the optimal crane pick sequence? |
| 4 | `optimize_routes` | VRP nearest-neighbour + 2-opt | What's the fastest delivery route? |
| 5 | `calculate_sustainability` | IPCC AR6 emission factors | What's the carbon cost of this operation? |
| 6 | `analyze_supply_network` | NetworkX betweenness centrality | Where's the single point of failure? |
| 7 | `check_shipping_compliance` | HS codes + CARICOM duty rules | What's the customs declaration and landed cost? |

---

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- An OpenAI API key (`https://platform.openai.com/api-keys`)

### Run

**1. Edit `.env` — add your OpenAI key:**
```
OPENAI_API_KEY=sk-your-key-here
```

**2. Start the agent:**
```bash
docker compose up
```

**3. Open the UI:**
```
http://localhost:8501
```

---

## Example Queries

```
What is the single point of failure in our Caribbean logistics network?
What should we reorder for Port of Spain this week?
Optimise the warehouse pick sequence for WH-POS-001
Generate a customs declaration for shipping rice and chicken from Trinidad to Barbados
Plan the most carbon-efficient route from Port of Spain to all Trinidad stores
```

---

## Project Structure

```
massy-agent/
├── agent/
│   ├── massy_agent.py    # Agent loop, OpenAI client, system prompt
│   └── app.py            # Streamlit chat UI with tool-call trace
├── tools/
│   ├── massy_tools.py    # All 7 tool implementations (boto3 → DynamoDB)
│   └── schemas.py        # OpenAI function-calling schemas
├── terraform/
│   ├── main.tf           # AWS provider
│   ├── variables.tf      # Region, project name, environment
│   ├── landing.tf        # S3 static landing page
│   └── reviewer.tf       # Read-only IAM user for AWS console access
├── landing/
│   └── index.html        # Public landing page (deployed to S3)
├── data/
│   └── seed.py           # Populates DynamoDB with Caribbean supply chain data
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env                  # Local secrets — never commit
```

---

## AWS Infrastructure

| Resource | Name |
|----------|------|
| DynamoDB — Inventory | `massy-agent-inventory` |
| DynamoDB — Orders | `massy-agent-orders` |
| DynamoDB — Locations | `massy-agent-locations` |
| S3 — Data | `massy-agent-data-prod` |
| S3 — Landing page | `massy-agent-landing-prod` |
| Region | `us-east-1` |

**AWS Console (read-only):**
```
Account:  901235308440
Login:    https://901235308440.signin.aws.amazon.com/console
```

---

## Caribbean Location Network

```
Trinidad (Hub)
├── WH-POS-001  Port of Spain Warehouse
├── STR-POS-001 Massy Stores Long Circular
├── STR-SFD-001 Massy Stores San Fernando
└── STR-CHG-001 Massy Stores Chaguanas

Tobago       — sea freight 35km / 2.5hr
└── STR-SCR-001 Massy Stores Scarborough

Barbados     — sea freight 440km / 24hr
├── WH-BGI-001  Bridgetown Distribution Hub
└── STR-BGI-001 Massy Stores Wildey

Guyana       — sea freight 560km / 30hr
└── STR-GEO-001 Massy Stores Georgetown

St. Lucia    — sea freight 480km / 26hr
└── STR-CAS-001 Massy Stores Castries
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | OpenAI gpt-4o-mini (function calling) |
| Agent orchestration | Custom Python loop |
| UI | Streamlit |
| Containerisation | Docker + Docker Compose |
| Data | AWS DynamoDB (boto3) |
| Infrastructure | Terraform (IaC) |
| ML / Algorithms | NetworkX, FP-Growth, 0-1 Knapsack DP, VRP |

---

## Author

**Sebastien Ghent**
MS Computer Science — University of South Florida
AI/ML Engineer · Cloud & Data Engineering · Agentic Systems