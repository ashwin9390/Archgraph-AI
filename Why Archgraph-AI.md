# ArchGraph AI
## Citation-Backed System Design Critique Engine

---

## The Problem It Solves

Every week, engineering teams make architecture decisions that have already failed at other companies — and those failures are documented publicly in engineering blogs. Discord wrote about why Cassandra destroyed their on-call team. Netflix wrote about why Chaos Engineering saved them from cascading failures. Stripe wrote about why missing idempotency keys causes duplicate charges. Philips HealthTech wrote about why a centralized WebSocket killed patient alarms during a network outage.

Nobody reads all of these. Nobody connects them to the architecture decisions they are making right now.

**The result:** A 3-person team installs self-managed Kafka because Netflix uses it — and six months later they are woken up at 2am by partition ring failures that Netflix has 50 engineers to handle.

ArchGraph AI exists to stop that from happening.

---

## What It Does

ArchGraph AI is a knowledge graph of engineering failure modes extracted from real production post-mortems. When you describe your architecture in plain English, it:

1. Parses your stack, team size, domain, and scale from free text
2. Queries the graph for matching failure patterns
3. Returns a **Scale Match Score** — how well the pattern fits your specific team size and scale
4. Cites the exact engineering blog post where the failure was documented

```
$ archgraph critique "self-managed kafka + cassandra, 3 backend engineers, 60k writes/sec"

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
  Migrate to a managed queue (AWS SQS/Kinesis, GCP Pub/Sub).
  Apply edge-batching at source nodes (Tesla Pattern) to reduce ingestion pressure.

  CITATIONS
   → https://discord.com/blog/how-discord-stores-trillions-of-messages
```

No hallucination. Every warning has a citation. Every recommendation comes from a company that actually ran it in production.

---

## Why This Didn't Exist Before

Every existing system design tool asks: **"What does Netflix use?"**

ArchGraph AI asks: **"Would what Netflix uses work for YOU — given your team size, domain, and scale?"**

That is a fundamentally different and more useful question. Netflix can run self-managed Kafka because they have 50 infrastructure engineers. You cannot. The technology is the same. The context is completely different. Existing tools ignore context entirely.

Other tools in this space:
- **System design interview prep sites** — teach patterns, not failure modes
- **Architecture review tools** — check against static rules, not real post-mortems
- **LLM-based advice** — hallucinate confidently with no citations
- **Consulting** — expensive, slow, unavailable to most teams

ArchGraph AI is the only tool that grounds every critique in a real, citable engineering post-mortem.

---

## The Scale Match Score

The most original feature. A score from 0.0 to 1.0 that answers: *"Is your team large enough to safely operate this pattern?"*

| Score | Meaning |
|---|---|
| 1.0 | Pattern is well-matched to your team size and scale |
| 0.5–0.9 | Proceed with caution — document the operational risk |
| < 0.5 | **HIGH RISK** — this pattern has destroyed teams your size |

Discord ran Cassandra at 177 nodes with a dedicated infrastructure team. A 3-person startup running the same setup gets a score of 0.3. The technology is identical. The risk is completely different.

---

## The Knowledge Graph

The graph stores engineering patterns as nodes with edges encoding relationships:

- `REPLACED` — "ScyllaDB replaced Cassandra because..."
- `SUFFERED_NEGATIVE` — "Netflix suffered cascading failures from..."
- `CONSTRAINED_BY` — "Chaos Engineering is constrained by requiring a mature on-call rotation"

Current knowledge base includes failure modes and patterns from:

| Company | Domain | Patterns |
|---|---|---|
| Discord | RealTime / HighThroughput | ScyllaDB migration, Kafka elimination, WebSocket fanout |
| Netflix | WebScale / HighAvailability | Circuit Breaker (Hystrix), Chaos Engineering, Simian Army |
| Stripe | Finance / Payments | Idempotency Keys, at-most-once payment execution |
| Anthropic | AI Infrastructure | Parallel Router-Classifier, KV-cache recycling |
| Philips HealthTech | MedTech / IoMT | Hub-and-Spoke Edge, offline-first patient alarm architecture |
| Tesla | Edge / IoT | Edge telemetry pre-aggregation, fleet batching |

---

## Domain Coverage

ArchGraph AI covers five distinct engineering domains — each with different failure modes:

**WebScale / Microservices** — Kafka, Cassandra, Circuit Breakers, Chaos Engineering. The failure modes here are mostly about operational complexity outpacing team size.

**Finance / Payments** — Idempotency, at-most-once execution, audit trails. The failure modes here are about correctness under network failure — a bug that causes a duplicate charge is not a performance problem, it is a compliance incident.

**AI Infrastructure** — Sequential agent chains, KV-cache pressure, parallel execution. The failure modes here are about latency explosion under load — a sequential chain that works at 10 docs/hour silently fails at 1,000.

**MedTech / IoMT** — FDA SaMD compliance, patient alarm architecture, HIPAA. The failure modes here are literally life-critical. A centralized WebSocket for patient vitals is not a performance concern — it is an FDA violation and a patient safety risk.

**Edge / IoT** — Telemetry batching, fleet management, hardware co-design. The failure modes here are about bandwidth and operational cost — direct-streaming from a million devices is not a scalability problem, it is financially untenable.

---

## How It Works

```
Your architecture description (free text)
           ↓
    ArchInput Parser
    (extracts: team size, stack keywords, domain, WPS, latency targets)
           ↓
    Rule Engine + Graph Query
    (matches patterns from knowledge graph by keyword + domain)
           ↓
    Scale Match Score calculation
    (team_size / pattern.team_size_min)
           ↓
    Critique Report
    (risk level, evidence, recommended pivot, citations)
```

The graph uses an in-memory backend by default (zero dependencies) and supports Neo4j for production deployments with relationship traversal.

---

## Who It Is For

**Early-stage engineering teams (2–10 engineers)** making architecture decisions without a dedicated infrastructure team or principal engineer. These are the teams most likely to copy a pattern from a 500-engineer company without understanding the operational cost.

**Tech leads and principal engineers** doing architecture review. ArchGraph AI surfaces failure modes they may not have seen before, backed by production evidence.

**Engineering educators and system design interviewers** who want to teach failure modes, not just patterns.

**MedTech and FinTech teams** where architecture mistakes have compliance and safety consequences, not just operational ones.

---

## What Makes It Different

| Feature | ArchGraph AI | LLM Chat | Interview Prep Sites |
|---|---|---|---|
| Citation for every warning | ✅ | ❌ | ❌ |
| Team-size awareness | ✅ | ❌ | ❌ |
| Scale Match Score | ✅ | ❌ | ❌ |
| Domain-specific failure modes | ✅ | Partial | ❌ |
| Grounded in production post-mortems | ✅ | ❌ | ❌ |
| Works offline | ✅ | ❌ | ❌ |
| Free text input | ✅ | ✅ | ❌ |

---

## Why It Was Created

The idea came from a simple observation: the information needed to make better architecture decisions already exists — it is in public engineering blogs from Discord, Netflix, Stripe, Anthropic, Philips, and Tesla. The problem is nobody has extracted the *failure conditions* from those posts and made them queryable against your specific context.

Every system design book teaches patterns. Nobody teaches when a pattern becomes dangerous. ArchGraph AI was built to answer exactly that question — not with opinions, but with evidence.

---

## Current Status

- ✅ CLI working (`archgraph critique "..."`)
- ✅ REST API (FastAPI)
- ✅ 8 seed techniques from 6 companies
- ✅ In-memory graph (zero dependencies)
- ✅ Neo4j backend (optional)
- ✅ 43 tests passing
- ✅ GitHub Actions CI
- 🔲 LLM-assisted technique extraction from blog posts (next)
- 🔲 Community technique registry via GitHub PRs (next)
- 🔲 Web UI (planned)
- 🔲 GitHub Action for PR-level architecture review (planned)

---

## GitHub

[github.com/ashwin9390/archgraph-ai](https://github.com/ashwin9390)
