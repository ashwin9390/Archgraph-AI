# Contributing to ArchGraph AI

Thank you for helping grow the knowledge graph! There are two ways to contribute:

---

## 1. Add a new technique to `seed_data.py`

This is the **highest-value contribution**. Every technique you add gives every user better critiques.

Open `archgraph/graph/seed_data.py` and add an entry following this template:

```python
{
    "technique_id": "company_short_name",          # snake_case, unique
    "name": "Human-readable technique name",
    "origin_company": "CompanyName",
    "source_url": "https://real-engineering-blog-post-url",
    "domain_tags": ["WebScale"],                   # from the list below
    "design_techniques": ["Pattern A", "Pattern B"],
    "positive_outcomes": [
        "Metric or qualitative outcome with numbers where possible",
    ],
    "negative_side_effects": [
        "Real cost or operational burden",
    ],
    "counter_indicators": [
        "Condition under which this pattern is a bad idea",
    ],
    "scale_context": {
        "team_size_min": 3,                        # minimum team to operate this
    },
}
```

**Valid domain_tags:**
`WebScale`, `Microservices`, `HighAvailability`, `RealTime`, `HighThroughput`,
`Infrastructure`, `DataEngineering`, `MLOps`, `AIInfra`, `Finance`, `Payments`,
`Compliance`, `Security`, `MedTech`, `IoMT`, `EdgeIoT`, `HardwareCoDesign`,
`Cloud`, `Serverless`, `EdgeComputing`

**Rules:**
- Source URL must be a real, publicly accessible engineering blog post
- Do not reproduce copyrighted text verbatim — write outcomes in your own words
- Every technique needs at least one `counter_indicator`
- Every technique needs `scale_context.team_size_min`

---

## 2. Fix a bug or add a feature

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/archgraph-ai
cd archgraph-ai

# 2. Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install in editable mode with dev deps
pip install -e ".[dev]"

# 4. Run tests (all pass offline — no Neo4j needed)
pytest tests/ -v

# 5. Run the CLI to manually verify
archgraph critique "kafka cassandra 3 engineers 60k writes/sec"

# 6. Lint
ruff check archgraph tests

# 7. Open a PR
```

---

## Local Neo4j (optional)

If you want to test with a real graph backend:

```bash
docker-compose up neo4j
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=archgraph
archgraph critique "kafka 3 engineers"
```

---

## Code of Conduct

Be kind. Focus on technical merit. Welcome newcomers.
