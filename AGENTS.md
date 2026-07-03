# Massy Supply Chain Agent — Repository Context

Agentic AI supply chain demo for Massy Group's Caribbean distribution network (Trinidad, Tobago, Barbados, Guyana, St. Lucia). The agent reasons via **OpenAI tool-calling** (default model: `gpt-4o-mini`) and reads live enterprise data from **AWS DynamoDB** via boto3. Enterprise data stays in AWS; only tool inputs/outputs flow through the model.

---

## Architecture

```
Streamlit UI (agent/app.py)
        │
        ▼
MassyAgent loop (agent/massy_agent.py)
  · OpenAI chat completions + function calling
  · max 8 tool-call steps
        │
        ▼
Tool registry (tools/massy_tools.py)
  · 7 Python functions
  · boto3 → DynamoDB tables
        │
        ▼
AWS data layer (provisioned elsewhere; tables named {PROJECT_NAME}-*)
  · inventory · orders · locations
```

**Deployment:** Single Docker service (`docker compose up`) exposing Streamlit on port **8501**.

**Static marketing site:** `landing/index.html` deployed to S3 via `terraform/landing.tf`.

---

## Directory layout

| Path | Purpose |
|------|---------|
| `agent/app.py` | Streamlit chat UI; caches `MassyAgent`, shows tool-call trace |
| `agent/massy_agent.py` | Agent loop, system prompt, OpenAI client, CLI entry (`python massy_agent.py "query"`) |
| `tools/massy_tools.py` | All 7 tool implementations + `TOOLS` dict |
| `tools/schemas.py` | OpenAI function-calling `TOOL_SCHEMAS` |
| `terraform/landing.tf` | S3 static website for landing page |
| `terraform/reviewer.tf` | IAM read-only reviewer user for AWS console access |
| `landing/index.html` | Portfolio/demo landing page (dark green terminal aesthetic) |
| `Dockerfile` | Python 3.11 slim; runs Streamlit |
| `docker-compose.yml` | Agent service + `.env` file |
| `.env` | Secrets — **never commit or copy into docs** |

---

## Environment variables

| Variable | Default | Used by |
|----------|---------|---------|
| `OPENAI_API_KEY` | — | `MassyAgent` (required) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Agent + UI sidebar |
| `AWS_ACCESS_KEY_ID` | — | boto3 |
| `AWS_SECRET_ACCESS_KEY` | — | boto3 |
| `AWS_REGION` | `us-east-1` | boto3 |
| `PROJECT_NAME` | `massy-agent` | DynamoDB table name prefix |

DynamoDB tables: `{PROJECT_NAME}-inventory`, `{PROJECT_NAME}-orders`, `{PROJECT_NAME}-locations`.

---

## The 7 tools

Registered in `TOOLS` (`massy_tools.py`) and described in `TOOL_SCHEMAS` (`schemas.py`):

| Tool | Algorithm / approach | Data source |
|------|---------------------|-------------|
| `get_inventory_status` | Reorder thresholds, days-of-supply | DynamoDB inventory + `LocationIndex` GSI |
| `get_demand_forecast` | Basket analysis, association rules | DynamoDB orders + `LocationDateIndex` GSI |
| `optimize_warehouse` | 0-1 knapsack DP | Hardcoded job list (demo data) |
| `optimize_routes` | Nearest-neighbour + 2-opt VRP | `LOCATIONS`, `SEA_ROUTES`, haversine |
| `calculate_sustainability` | IPCC-style emission factors | Constants in `massy_tools.py` |
| `analyze_supply_network` | NetworkX betweenness + co-purchase communities | `ROUTE_EDGES` + orders scan |
| `check_shipping_compliance` | HS codes, CARICOM duty, VAT | `HS_CODES`, `CARICOM`, `VAT` constants |

**Agent chaining guidance** (from system prompt in `massy_agent.py`):
- Reorders → inventory → forecast → routes → sustainability
- Warehouse → optimizer → sustainability
- Cross-border → always `check_shipping_compliance`
- Network risk → `analyze_supply_network`

Responses should quantify in **TTD**, **km**, and **kg CO₂**.

---

## Key domain constants

- **Location IDs:** `WH-POS-001`, `STR-POS-001`, `STR-BGI-001`, etc. — see `LOCATIONS` dict in `massy_tools.py`
- **SKU IDs:** `RICE-5KG`, `CHICKEN-WHOLE`, `FLOUR-2KG`, etc.
- **Islands:** Trinidad, Tobago, Barbados, Guyana, St. Lucia

When adding tools, update **three places**: function in `massy_tools.py`, entry in `TOOLS`, schema in `schemas.py`.

---

## Running locally

```bash
docker compose up --build
# UI: http://localhost:8501

# CLI (inside container):
docker compose exec agent python agent/massy_agent.py "your question"
```

Requires valid OpenAI and AWS credentials in `.env` or shell environment.

---

## Terraform

Partial config in this repo (expects external `variables.tf` / backend for full apply):

- **`landing.tf`** — public S3 bucket `{project_name}-landing-{environment}`, hosts `landing/index.html`
- **`reviewer.tf`** — IAM user `massy-reviewer` with `ReadOnlyAccess`

Variables referenced: `var.project_name`, `var.environment`, `var.aws_region`.

---

## Conventions for contributors

- **Python 3.11**, minimal dependencies (`requirements.txt`: openai, boto3, streamlit, networkx)
- Tools return JSON-serializable dicts; agent loop uses `json.dumps(..., default=str)` for tool results
- Logging: `massy.agent`, `massy.tools`
- UI styling: IBM Plex fonts, green/navy terminal theme in `app.py`
- Landing page: Space Mono + Syne, CSS variables in `:root`
- Keep changes focused — tools, agent prompt, and schemas stay in sync
- Do not add secrets to tracked files; `.env` is local-only

---

## Example queries

- "What is the single point of failure in our Caribbean logistics network?"
- "What should we reorder for Port of Spain this week?"
- "Optimise the warehouse pick sequence for WH-POS-001"
- "Generate a customs declaration for shipping rice and chicken from Trinidad to Barbados"
