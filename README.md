# ArchGraph AI

**Citation-backed system design critique engine.** Paste your architecture. Get failures predicted — with real engineering post-mortem evidence.

```
$ archgraph critique "self-managed kafka + cassandra, 3 backend engineers, 60k writes/sec"

══════════════════════════════════════════════════════════════════════
  ArchGraph AI — Architecture Critique Report
══════════════════════════════════════════════════════════════════════
  Architecture : self-managed kafka + cassandra, 3 backend engineers
  Team Size    : 3 engineers
  Domain       : General
  Overall Risk : CRITICAL
══════════════════════════════════════════════════════════════════════

  ❌ [CRITICAL] Self-Managed Kafka with Insufficient Team Bandwidth
  Scale Match Score: 0.6 ← TEAM TOO SMALL

  PROBLEM
  A self-managed Kafka cluster requires dedicated infrastructure engineers
  for partition rebalancing, broker upgrades, and compaction tuning.
  Teams under 5 engineers routinely experience operational collapse
  during partition ring failures.

  ENGINEERING SCARS (from production post-mortems)
   • Migration required dual-write period with operational complexity
   • Team needed to learn ScyllaDB tuning parameters from scratch

  RECOMMENDED PIVOT
  Migrate to a managed queue (AWS SQS/Kinesis, GCP Pub/Sub, Confluent Cloud).
  Apply edge-batching at source nodes (Tesla Pattern) to reduce ingestion pressure.

  CITATIONS
   → https://discord.com/blog/how-discord-stores-trillions-of-messages

```

---

## The Problem It Solves

Every week, engineering teams make architecture decisions that have already failed at other companies — and those failures are documented publicly in engineering blogs. Discord wrote about why Cassandra destroyed their on-call team; Netflix wrote about why Chaos Engineering saved them from cascading failures; Stripe wrote about why missing idempotency keys causes duplicate charges; and Philips HealthTech wrote about why a centralized WebSocket killed patient alarms during a network outage.

**The result:** A 3-person team installs self-managed Kafka because Netflix uses it — and six months later they are woken up at 2am by partition ring failures that Netflix has 50 engineers to handle.

---

## What It Does

ArchGraph AI is a knowledge graph of **engineering failure modes** extracted from real production post-mortems. When you describe your architecture in plain English, the engine:

1. **Parses** your stack, team size, domain, and scale from free text.


2. **Queries** the graph for matching failure patterns.


3. **Returns a Scale Match Score** — how well the pattern fits your specific team size and scale.


4. **Cites** the exact engineering blog post where the failure was documented.


5. **Generates a Best-Design Blueprint** — a target architecture with an implementation checklist.



---

## Why This Didn't Exist Before

Every existing system design tool asks: **"What does Netflix use?"** ArchGraph AI asks: **"Would what Netflix uses work for YOU — given your team size, domain, and scale?"**

The technology is the same, but the context is completely different. Existing tools ignore context, teach only patterns, or provide hallucinations without citations.

---

## Domain Coverage

ArchGraph AI covers five distinct engineering domains:

* **WebScale / Microservices** — Kafka, Cassandra, Circuit Breakers, Chaos Engineering.


* **Finance / Payments** — Idempotency, at-most-once execution, audit trails.


* **AI Infrastructure** — Sequential agent chains, KV-cache pressure, parallel execution.


* **MedTech / IoMT** — FDA SaMD compliance, patient alarm architecture, HIPAA.


* **Edge / IoT** — Telemetry batching, fleet management, hardware co-design.



---

## Validation (Test Results)

ArchGraph AI is built for reliability. Every build is validated against our knowledge graph of engineering patterns.

```text
# Date: 2026-07-04 | Platform: Linux
Ran 98 tests in 0.091s — ALL PASS ✅

SUITE BREAKDOWN:
  Suite 1  — Ingestion                           3 tests  ✅
  Suite 5  — Design Issues (13 rules)           26 tests  ✅
  Suite 12 — Design Blueprint (NEW)             18 tests  ✅
  ... (summarized list)

```

Full test report available in `Archgraph_Test_Results.md`.

---

## Quick Start (no Neo4j needed)

```bash
pip install archgraph-ai

# Critique an architecture (uses built-in in-memory graph)
archgraph critique "kafka cassandra 3 engineers 60k writes/sec"

# MedTech / HIPAA domain
archgraph critique --domain MedTech "websocket patient vitals monitoring, 4 engineers"

# JSON output (pipe to jq)
archgraph critique --json "sequential LLM agent chain pipeline 3 engineers" | jq .

```

---

## REST API & Neo4j Integration

* **REST API**: Use `uvicorn archgraph.api.main:app --reload` to start the server. Interactive docs are available at `http://localhost:8000/docs`.


* **Neo4j**: For persistent graph storage, use `docker-compose up` or export your `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`.



---

## Architecture Overview

```
archgraph/
├── ingestion/       # Async scraper (aiohttp + Playwright)
├── graph/           # Neo4j + in-memory backends
├── critic/          # Rule engine + Scale Match Score
├── api/             # FastAPI REST layer
└── cli.py           # CLI entry point

```

---

## Current Status

* ✅ CLI working; REST API (FastAPI) implemented


* ✅ 8 seed techniques from 6 companies


* ✅ 98 tests passing; GitHub Actions CI active


* 🔲 **AI Agent Integration**: MCP server for native Claude/Gemini invocation.


* 🔲 LLM-assisted technique extraction; Community registry via PRs.



---

## 👤 Author & License

* **Author**: Ashwin H — [@ashwin9390](https://github.com/ashwin9390)

* **License**: Apache 2.0. See [LICENSE](https://github.com/ashwin9390/Archgraph-AI/blob/main/LICENSE)


* **GitHub**: [github.com/ashwin9390/archgraph-ai](https://github.com/ashwin9390/Archgraph-AI))
