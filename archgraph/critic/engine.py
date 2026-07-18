"""
ArchGraph AI — Critic Engine
Generates:
  1. Citation-backed critique of what is WRONG
  2. Best-design BLUEPRINT of what the correct architecture looks like
     for the specific stack, team size, domain, and scale detected.

Rule categories:
  OPERATIONAL  — wrong infra for team size / scale
  DESIGN       — structural problems (SPOF, missing resilience, sync anti-patterns)
  SECURITY     — auth, TLS gaps
  OBSERVABILITY — monitoring, tracing, runbook gaps
  ML_INFRA     — ML-specific: skew, versioning, feedback loops
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("archgraph.critic")

# ---------------------------------------------------------------------------
# Risk levels
# ---------------------------------------------------------------------------
RISK_CRITICAL = "CRITICAL"
RISK_WARNING  = "WARNING"
RISK_INFO     = "INFO"
RISK_OK       = "OK"

# ---------------------------------------------------------------------------
# Scale Match Score
# ---------------------------------------------------------------------------
def _scale_match_score(technique: dict, team_size: int) -> float:
    ctx = technique.get("scale_context", {})
    if isinstance(ctx, str):
        try:
            import ast
            ctx = ast.literal_eval(ctx)
        except Exception:
            ctx = {}
    min_team = ctx.get("team_size_min", 1)
    if team_size >= min_team:
        return 1.0
    return round(max(0.0, team_size / max(min_team, 1)), 2)


# ---------------------------------------------------------------------------
# Input parser
# ---------------------------------------------------------------------------
@dataclass
class ArchitectureInput:
    raw_description:   str
    stack_keywords:    list[str] = field(default_factory=list)
    team_size:         int = 5
    domain:            Optional[str] = None
    target_latency_ms: Optional[int] = None
    writes_per_second: Optional[int] = None

    @classmethod
    def from_text(cls, text: str) -> "ArchitectureInput":
        text_lower = text.lower()

        team_size = 5
        team_match = re.search(
            r"(\d+)\s*(backend|infra|engineer|developer|dev|person|people|member)",
            text_lower,
        )
        if team_match:
            team_size = int(team_match.group(1))

        wps = None
        wps_match = re.search(
            r"([\d,]+)\s*(writes?|events?|messages?|req)[\s/]*(per\s+)?se?c", text_lower
        )
        if wps_match:
            wps = int(wps_match.group(1).replace(",", ""))

        latency = None
        lat_match = re.search(r"under?\s*([\d.]+)\s*(ms|seconds?|s\b)", text_lower)
        if lat_match:
            val  = float(lat_match.group(1))
            unit = lat_match.group(2)
            latency = int(val * 1000) if "sec" in unit or unit == "s" else int(val)

        domain = None
        if any(w in text_lower for w in ["hipaa", "fda", "patient", "medtech", "iomt", "vitals", "ehr"]):
            domain = "MedTech"
        elif any(w in text_lower for w in ["payment", "transaction", "stripe", "finance", "banking"]):
            domain = "Finance"
        elif any(w in text_lower for w in ["llm", "agent", "mlops", "vector", "inference", "kv-cache"]):
            domain = "AIInfra"

        TECH_KEYWORDS = [
            "kafka", "rabbitmq", "sqs", "sns", "kinesis", "pubsub", "nats",
            "cassandra", "scylladb", "redis", "postgres", "mysql", "mongodb",
            "dynamodb", "elasticsearch", "neo4j", "sqlite",
            "kubernetes", "k8s", "docker", "serverless", "lambda",
            "websocket", "grpc", "rest", "graphql", "http", "rpc",
            "airflow", "spark", "flink",
            "microservice", "monolith", "event sourcing", "cqrs", "saga",
            "circuit breaker", "bulkhead", "sidecar", "service mesh",
            "rate limit", "rate limiting", "throttle", "throttling",
            "retry", "timeout", "fallback", "cache", "caching",
            "cdn", "load balanc",
            "llm", "vector db", "embedding", "rag", "agent", "sequential",
            "self-managed", "self managed", "managed", "hosted",
            "monitor", "observ", "tracing", "logging", "alert", "metric",
            "auth", "jwt", "oauth", "api key", "tls", "ssl",
            "ml", "model", "train", "feature", "recommend", "ranking",
            "batch inference", "feature store",
        ]
        keywords = [kw for kw in TECH_KEYWORDS if kw in text_lower]
        acronyms = re.findall(r"\b[A-Z]{2,6}\b", text)
        keywords += [a.lower() for a in acronyms]

        return cls(
            raw_description   = text,
            stack_keywords    = list(set(keywords)),
            team_size         = team_size,
            domain            = domain,
            target_latency_ms = latency,
            writes_per_second = wps,
        )


# ---------------------------------------------------------------------------
# Design Blueprint — what GOOD looks like for this specific stack
# ---------------------------------------------------------------------------
@dataclass
class BlueprintLayer:
    layer:     str    # e.g. "API Layer"
    component: str    # e.g. "REST API + nginx load balancer + rate limiting"
    why:       str    # one-line rationale
    source:    str    # which company/pattern this comes from


@dataclass
class DesignBlueprint:
    """
    Recommended best design for this specific architecture.
    Generated from knowledge graph patterns + detected issues.
    """
    title:         str
    summary:       str
    layers:        list[BlueprintLayer]
    checklist:     list[str]    # concrete things to implement
    anti_patterns: list[str]    # what NOT to do — from issues found
    citations:     list[str]

    def render_text(self) -> str:
        lines = [
            "",
            "=" * 70,
            "  ArchGraph AI — Recommended Best Design",
            "=" * 70,
            f"  {self.title}",
            "",
            f"  {self.summary}",
            "",
        ]
        if self.layers:
            lines += [f"{'─'*70}", "  🏗  ARCHITECTURE LAYERS", f"{'─'*70}", ""]
            for layer in self.layers:
                lines += [
                    f"  ┌─ {layer.layer}",
                    f"  │  Component : {layer.component}",
                    f"  │  Why       : {layer.why}",
                    f"  │  Pattern   : {layer.source}",
                    "  │",
                ]
            lines.append("")
        if self.checklist:
            lines += [f"{'─'*70}", "  ✅ IMPLEMENTATION CHECKLIST", f"{'─'*70}", ""]
            for i, item in enumerate(self.checklist, 1):
                lines.append(f"  {i:02d}. {item}")
            lines.append("")
        if self.anti_patterns:
            lines += [f"{'─'*70}", "  🚫 WHAT NOT TO DO (from post-mortems)", f"{'─'*70}", ""]
            for ap in self.anti_patterns:
                lines.append(f"   ✗ {ap}")
            lines.append("")
        if self.citations:
            lines += [f"{'─'*70}", "  📚 CITATIONS", f"{'─'*70}", ""]
            for c in self.citations:
                lines.append(f"   → {c}")
        lines.append("=" * 70)
        return "\n".join(lines)

    def render_dict(self) -> dict:
        return {
            "title":         self.title,
            "summary":       self.summary,
            "layers":        [
                {"layer": l.layer, "component": l.component,
                 "why": l.why, "source": l.source}
                for l in self.layers
            ],
            "checklist":     self.checklist,
            "anti_patterns": self.anti_patterns,
            "citations":     self.citations,
        }


# ---------------------------------------------------------------------------
# Critique output
# ---------------------------------------------------------------------------
@dataclass
class CritiqueItem:
    risk_level:        str
    category:          str   # OPERATIONAL | DESIGN | SECURITY | OBSERVABILITY
    title:             str
    problem:           str
    evidence:          list[str]
    pivot:             str
    citations:         list[str]
    scale_match_score: float = 1.0
    technique_id:      str = ""


@dataclass
class CritiqueReport:
    architecture_summary: str
    team_size:    int
    domain:       Optional[str]
    items:        list[CritiqueItem]
    overall_risk: str = RISK_OK
    blueprint:    Optional[DesignBlueprint] = None

    def render_text(self) -> str:
        operational   = [i for i in self.items if i.category == "OPERATIONAL"]
        design        = [i for i in self.items if i.category == "DESIGN"]
        security      = [i for i in self.items if i.category == "SECURITY"]
        observability = [i for i in self.items if i.category == "OBSERVABILITY"]

        lines: list[str] = [
            "=" * 70,
            "  ArchGraph AI — Architecture Critique Report",
            "=" * 70,
            f"  Architecture : {self.architecture_summary[:80]}",
            f"  Team Size    : {self.team_size} engineers",
            f"  Domain       : {self.domain or 'General'}",
            f"  Overall Risk : {self.overall_risk}",
            f"  Issues found : {len(self.items)} "
            f"({len(operational)} operational / {len(design)} design / "
            f"{len(security)} security / {len(observability)} observability)",
            "=" * 70,
        ]

        if not self.items:
            lines += ["", "  ✅  No critical issues detected.", ""]
        else:
            for section_title, section_items in [
                ("🔧 OPERATIONAL RISKS", operational),
                ("🏗  DESIGN ISSUES",    design),
                ("🔒 SECURITY ISSUES",   security),
                ("📊 OBSERVABILITY GAPS", observability),
            ]:
                if not section_items:
                    continue
                lines.append(f"\n{'─'*70}")
                lines.append(f"  {section_title}")
                lines.append(f"{'─'*70}")
                for item in section_items:
                    icon = {"CRITICAL": "❌", "WARNING": "⚠️ ",
                            "INFO": "ℹ️ ", "OK": "✅"}.get(item.risk_level, "ℹ️ ")
                    lines += ["", f"  {icon} [{item.risk_level}] {item.title}"]
                    if item.scale_match_score < 1.0:
                        suffix = " ← TEAM TOO SMALL" if item.scale_match_score < 0.5 else ""
                        lines.append(f"  Scale Match Score: {item.scale_match_score}/1.0{suffix}")
                    lines += ["", "  PROBLEM", f"  {item.problem}", ""]
                    if item.evidence:
                        lines.append("  ENGINEERING SCARS (from production post-mortems)")
                        for ev in item.evidence:
                            lines.append(f"   • {ev}")
                        lines.append("")
                    lines += ["  RECOMMENDED FIX", f"  {item.pivot}", "", "  CITATIONS"]
                    for c in item.citations:
                        lines.append(f"   → {c}")
                    lines.append("-" * 70)

        if self.blueprint:
            lines.append(self.blueprint.render_text())

        return "\n".join(lines)

    def render_dict(self) -> dict:
        d = {
            "architecture_summary": self.architecture_summary,
            "team_size":    self.team_size,
            "domain":       self.domain,
            "overall_risk": self.overall_risk,
            "critique_items": [
                {
                    "risk_level":        it.risk_level,
                    "category":          it.category,
                    "title":             it.title,
                    "problem":           it.problem,
                    "evidence":          it.evidence,
                    "pivot":             it.pivot,
                    "citations":         it.citations,
                    "scale_match_score": it.scale_match_score,
                }
                for it in self.items
            ],
        }
        if self.blueprint:
            d["best_design"] = self.blueprint.render_dict()
        return d


_RULES: list[dict] = [

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY A — OPERATIONAL RISKS
    # ══════════════════════════════════════════════════════════════════════

    {
        "id":             "kafka_small_team",
        "category":       "OPERATIONAL",
        "triggers":       ["kafka", "self-managed", "self managed"],
        "team_threshold": 5,
        "risk":           RISK_CRITICAL,
        "title":          "Self-Managed Kafka with Insufficient Team Bandwidth",
        "problem": (
            "A self-managed Kafka cluster requires dedicated infrastructure engineers "
            "for partition rebalancing, broker upgrades, and compaction tuning. "
            "Teams under 5 engineers routinely experience operational collapse during "
            "partition ring failures."
        ),
        "evidence_keys": ["negative_side_effects", "counter_indicators"],
        "pivot": (
            "Migrate to a managed queue (AWS SQS/Kinesis, GCP Pub/Sub, Confluent Cloud). "
            "Apply edge-batching at source nodes (Tesla Pattern) to reduce ingestion pressure."
        ),
    },
    {
        "id":             "cassandra_small_team",
        "category":       "OPERATIONAL",
        "triggers":       ["cassandra", "self-managed"],
        "team_threshold": 5,
        "risk":           RISK_CRITICAL,
        "title":          "Self-Managed Cassandra with Insufficient Team Bandwidth",
        "problem": (
            "Cassandra compaction, repair cycles, and partition ring management "
            "require dedicated infrastructure expertise. Discord migrated away from "
            "Cassandra (177 nodes → 72 ScyllaDB nodes) because GC-induced tail "
            "latency was unmanageable at their team size."
        ),
        "evidence_keys": ["negative_side_effects"],
        "pivot": (
            "Consider ScyllaDB (shared-nothing, lower GC pressure) or DynamoDB/Cassandra-as-a-Service. "
            "Require at minimum 2 dedicated infrastructure engineers if staying on Cassandra."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY B — DESIGN ISSUES
    # ══════════════════════════════════════════════════════════════════════

    # ── Resilience ────────────────────────────────────────────────────────
    {
        "id":             "missing_circuit_breaker",
        "category":       "DESIGN",
        "triggers":       ["microservice", "grpc", "rest", "http", "rpc", "service mesh"],
        "anti_triggers":  ["circuit breaker", "hystrix", "resilience4j", "bulkhead"],
        "team_threshold": 99,
        "risk":           RISK_CRITICAL,
        "title":          "No Circuit Breaker — Cascading Failure Risk",
        "problem": (
            "Microservice architectures without circuit breakers propagate failures "
            "across service boundaries. A single slow downstream service causes thread "
            "pool exhaustion upstream, taking down the entire call chain. "
            "Netflix experienced cascading failures across 600+ microservices before "
            "implementing Hystrix circuit breakers."
        ),
        "evidence_keys": ["positive_outcomes", "negative_side_effects"],
        "pivot": (
            "Implement circuit breakers on all synchronous inter-service calls. "
            "Use Netflix Hystrix pattern: open circuit after 5 failures in 10s, "
            "return fallback response, half-open after 30s to probe recovery. "
            "Resilience4j (Java), resilience (Python), or Envoy sidecar all work."
        ),
        "citations": [
            "https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d"
        ],
    },
    {
        "id":             "missing_rate_limiting",
        "category":       "DESIGN",
        "triggers":       ["rest", "graphql", "api", "http", "grpc", "public"],
        "anti_triggers":  ["rate limit", "rate limiting", "throttle", "throttling"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "No Rate Limiting on API — Abuse and Overload Risk",
        "problem": (
            "APIs without rate limiting are vulnerable to abuse, accidental overload "
            "from runaway clients, and DDoS amplification. A single misbehaving client "
            "can consume all available connections and cause total service unavailability "
            "for legitimate users. This is especially dangerous for public-facing APIs."
        ),
        "evidence_keys": [],
        "pivot": (
            "Implement per-client rate limiting at the API gateway or load balancer level. "
            "Use token bucket algorithm for burst tolerance. "
            "Recommended limits: 100 req/min per API key for read, 20 req/min for write. "
            "Return 429 Too Many Requests with Retry-After header. "
            "Tools: Kong, AWS API Gateway, nginx limit_req, Redis + sliding window."
        ),
        "citations": [
            "https://stripe.com/blog/rate-limiters",
            "https://cloud.google.com/architecture/rate-limiting-strategies-techniques",
        ],
    },
    {
        "id":             "missing_retry_timeout",
        "category":       "DESIGN",
        "triggers":       ["microservice", "grpc", "rest", "http", "rpc", "downstream"],
        "anti_triggers":  ["retry", "timeout", "backoff", "deadline"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "No Retry / Timeout Strategy — Silent Failure Risk",
        "problem": (
            "Services that call downstream dependencies without explicit timeouts "
            "accumulate hanging connections during partial failures. Without retry "
            "logic, transient network errors cause permanent user-visible failures. "
            "Without exponential backoff, retry storms during recovery can re-collapse "
            "a service that is just coming back online."
        ),
        "evidence_keys": [],
        "pivot": (
            "Set explicit timeouts on every outbound call (recommend: p99 latency × 3). "
            "Implement exponential backoff with jitter on retries (max 3 attempts). "
            "Use deadline propagation — if the upstream request has 200ms left, "
            "do not set a 500ms timeout on the downstream call. "
            "Never retry non-idempotent write operations without idempotency keys."
        ),
        "citations": [
            "https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/",
        ],
    },
    {
        "id":             "synchronous_chain_latency",
        "category":       "DESIGN",
        "triggers":       ["microservice", "sequential", "chain", "service mesh",
                           "service-to-service", "downstream call"],
        "anti_triggers":  ["async", "event", "queue", "message", "pubsub", "kafka",
                           "rabbitmq", "sqs", "nats", "event sourcing"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "Deep Synchronous Service Chain — Latency Multiplication",
        "problem": (
            "Synchronous call chains multiply latency: if A calls B calls C calls D, "
            "the user-facing latency is A+B+C+D plus network overhead. A chain of "
            "4 services each averaging 50ms produces 200ms+ minimum latency before "
            "any business logic runs. Under load, tail latencies compound multiplicatively. "
            "This is a structural design problem — adding capacity does not fix it."
        ),
        "evidence_keys": [],
        "pivot": (
            "Identify which downstream calls can be made async via event queue. "
            "Use fan-out pattern for independent downstream calls (run in parallel). "
            "Cache stable downstream data at the edge service. "
            "Reserve synchronous chains for operations where the result is needed "
            "immediately by the user (< 3 service hops recommended). "
            "Consider event sourcing / CQRS for write paths that trigger multiple downstream effects."
        ),
        "citations": [
            "https://engineering.fb.com/2020/05/07/data-infrastructure/messenger/",
        ],
    },
    {
        "id":             "single_point_of_failure_db",
        "category":       "DESIGN",
        "triggers":       ["postgres", "mysql", "sqlite", "mongodb", "single", "primary"],
        "anti_triggers":  ["replica", "standby", "failover", "rds", "aurora", "cluster",
                           "replication", "multi-az", "ha"],
        "team_threshold": 99,
        "risk":           RISK_CRITICAL,
        "title":          "Single Database Instance — No Failover",
        "problem": (
            "A single database instance with no replica or standby is a hard single "
            "point of failure. Instance failure, disk corruption, or a botched migration "
            "causes complete service downtime with no automatic recovery path. "
            "Recovery from a snapshot typically takes 15–60 minutes minimum, "
            "during which the service is completely unavailable."
        ),
        "evidence_keys": [],
        "pivot": (
            "Add a read replica as a minimum for failover capability (promotes to primary in ~30s). "
            "For production: use managed multi-AZ (AWS RDS Multi-AZ, Aurora, GCP Cloud SQL HA). "
            "Implement automated failover — manual promotion takes too long under incident stress. "
            "Test failover quarterly; most teams discover it does not work during an actual incident."
        ),
        "citations": [
            "https://aws.amazon.com/rds/features/multi-az/",
        ],
    },
    {
        "id":             "no_caching_layer",
        "category":       "DESIGN",
        "triggers":       ["postgres", "mysql", "mongodb", "dynamodb", "cassandra",
                           "rest", "graphql", "api"],
        "anti_triggers":  ["redis", "memcached", "cache", "cdn", "caching", "varnish"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "No Caching Layer — Database Will Become the Bottleneck",
        "problem": (
            "Systems that hit the database on every request hit a hard scalability wall "
            "at moderate traffic levels. Read-heavy workloads (>70% reads) degrade "
            "database performance for writes, increasing latency across the board. "
            "Adding database capacity is expensive and has diminishing returns. "
            "Most application data has high read-to-write ratios and is cacheable."
        ),
        "evidence_keys": [],
        "pivot": (
            "Add Redis or Memcached as a read-through cache in front of the database. "
            "Cache aggressively for data with TTL > 1 second (user profiles, product catalog, "
            "configuration, session data). "
            "Use cache-aside pattern: read from cache, on miss read from DB and populate cache. "
            "For APIs: add CDN caching for public responses (CloudFront, Fastly). "
            "Target: 80%+ cache hit rate before scaling the database."
        ),
        "citations": [
            "https://engineering.fb.com/2013/06/25/core-infra/tao-the-power-of-the-graph/",
        ],
    },
    {
        "id":             "sequential_agent_chain",
        "category":       "DESIGN",
        "triggers":       ["sequential", "agent", "chain", "pipeline", "llm"],
        "anti_triggers":  ["parallel", "concurrent", "fan-out", "router"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "Sequential LLM Agent Chain — KV-Cache Stall and Latency Risk",
        "problem": (
            "Deep sequential agent chains cause compounding context growth. "
            "Each hop forces the LLM to re-process the accumulated context, causing "
            "KV-cache evictions and exponential latency growth under load. "
            "A 4-step sequential chain at 1,000 docs/hour will typically exceed "
            "a 3-second latency SLA."
        ),
        "evidence_keys": ["negative_side_effects"],
        "pivot": (
            "Shift to a Parallel Router-Classifier Architecture (Anthropic Pattern). "
            "Run independent extraction/validation branches in parallel. "
            "Merge metadata in a single final step using PagedAttention "
            "to recycle KV-cache entries across branches."
        ),
        "citations": [
            "https://anthropic.com/research/building-effective-agents",
        ],
    },
    {
        "id":             "centralized_websocket_medtech",
        "category":       "DESIGN",
        "triggers":       ["websocket", "vitals", "patient", "iomt", "ecg", "monitoring"],
        "team_threshold": 99,
        "risk":           RISK_CRITICAL,
        "title":          "Centralized WebSocket for Life-Critical Patient Vitals — FDA Violation Risk",
        "problem": (
            "Centralized cloud WebSocket servers for patient vitals monitoring introduce "
            "a catastrophic failure domain: if the hospital WAN drops, all alarms are silenced. "
            "This violates FDA SaMD Class II/III guidelines and Philips HealthTech's IoMT "
            "design safety paradigm for life-critical distributed topology."
        ),
        "evidence_keys": ["positive_outcomes", "negative_side_effects"],
        "pivot": (
            "Implement a Tiered Hub-and-Spoke Edge Architecture (Philips HealthTech Pattern). "
            "Move alarm logic fully onto an air-gapped bedside edge appliance. "
            "Use hardwired fail-safe relay alerts for life-critical thresholds. "
            "Asynchronously batch compressed, encrypted telemetry to cloud via offline-first sync."
        ),
        "citations": [
            "https://innovation.philips.com/blog/iomt-edge-architecture",
        ],
    },
    {
        "id":             "no_idempotency_payments",
        "category":       "DESIGN",
        "triggers":       ["payment", "transaction", "charge", "billing"],
        "anti_triggers":  ["idempotency", "idempotent", "deduplication"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "Missing Idempotency Keys for Payment Operations",
        "problem": (
            "Payment API calls without server-side idempotency keys create duplicate-charge "
            "risk during network retries. Stripe's production data shows this is the #1 "
            "cause of customer-visible payment bugs in distributed systems."
        ),
        "evidence_keys": ["positive_outcomes"],
        "pivot": (
            "Require client-generated idempotency keys on all payment mutations. "
            "Implement a persistent server-side deduplication store (Redis or DB row) "
            "with TTL ≥ 24 hours. Scope keys to (user_id, action_type, amount) tuple."
        ),
        "citations": [
            "https://stripe.com/blog/idempotency",
        ],
    },

    # ── Scalability (from system-design-primer) ───────────────────────────────
    {
        "id":             "missing_cdn",
        "category":       "DESIGN",
        "triggers":       ["static", "asset", "image", "video", "public", "frontend",
                           "react", "vue", "angular", "javascript", "css", "html"],
        "anti_triggers":  ["cdn", "cloudfront", "fastly", "cloudflare", "akamai",
                           "edge", "s3", "gcs bucket"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "No CDN — Static Assets Served from Origin, Global Latency Risk",
        "problem": (
            "Serving static assets (JS, CSS, images, video) directly from origin servers "
            "wastes bandwidth, increases p99 latency for users far from your data centre, "
            "and creates unnecessary load on application servers during traffic spikes. "
            "Without a CDN, a cache miss on a popular asset hits your origin every time. "
            "The system-design-primer documents CDN as a fundamental scalability primitive "
            "for any public-facing web product."
        ),
        "evidence_keys": ["positive_outcomes", "negative_side_effects"],
        "pivot": (
            "Add a CDN (CloudFront, Cloudflare, Fastly) in front of all static assets. "
            "Use pull CDN for infrequently changing assets — CDN caches on first request. "
            "Use push CDN for large known assets (video, large downloads). "
            "Set Cache-Control: max-age=31536000 with content-hashed filenames for static. "
            "Target: 90%+ CDN hit rate before scaling origin. "
            "Serve the React/Vue bundle from CDN, API calls from origin."
        ),
        "citations": [
            "https://github.com/donnemartin/system-design-primer#content-delivery-network",
            "https://github.com/ashishps1/awesome-system-design-resources",
        ],
    },
    {
        "id":             "missing_load_balancer",
        "category":       "DESIGN",
        "triggers":       ["microservice", "kubernetes", "k8s", "docker", "multiple",
                           "scale", "replica", "instance", "horizontal"],
        "anti_triggers":  ["load balanc", "nginx", "haproxy", "alb", "elb", "ingress",
                           "api gateway", "kong", "istio", "envoy", "traefik"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "No Load Balancer Mentioned — Single Point of Failure on Entry",
        "problem": (
            "Systems with multiple service instances or containers but no load balancer "
            "have no automatic traffic distribution or health-check-based failover. "
            "A single failed instance continues to receive traffic until manually removed. "
            "The system-design-primer identifies load balancing as a prerequisite for "
            "any horizontally-scaled architecture — without it, scaling adds capacity "
            "but not reliability."
        ),
        "evidence_keys": [],
        "pivot": (
            "Add a load balancer at every tier boundary. "
            "For Kubernetes: use an Ingress controller (nginx-ingress, Traefik) or "
            "a service mesh (Istio, Linkerd) for internal load balancing. "
            "For cloud: AWS ALB/NLB, GCP Load Balancer, or Azure Application Gateway. "
            "Configure health checks so failed pods are removed from rotation automatically. "
            "Use Layer 7 load balancing for HTTP — enables path-based routing and sticky sessions."
        ),
        "citations": [
            "https://github.com/donnemartin/system-design-primer#load-balancer",
            "https://github.com/ashishps1/awesome-system-design-resources",
        ],
    },
    {
        "id":             "cap_wrong_consistency",
        "category":       "DESIGN",
        "triggers":       ["payment", "transaction", "ledger", "banking", "inventory",
                           "stock", "eventual consistency", "dynamodb",
                           "cassandra", "mongodb"],
        "anti_triggers":  ["strong consistency", "linearizable", "serializable",
                           "acid", "2pc", "two-phase commit", "cp system",
                           "postgres", "postgresql", "mysql", "cockroachdb", "spanner"],
        "team_threshold": 99,
        "risk":           RISK_CRITICAL,
        "title":          "CAP Theorem Violation — Eventual Consistency on Financial / Inventory Data",
        "problem": (
            "Eventual consistency databases (Cassandra, DynamoDB in default mode, MongoDB "
            "with read preference secondary) on financial or inventory data create silent "
            "correctness bugs: double-charges, negative inventory, split-brain balances. "
            "The CAP theorem defines this tradeoff clearly — AP systems sacrifice consistency "
            "during network partitions. For financial data, a partition causing inconsistency "
            "is a compliance incident, not just a bug. "
            "The system-design-primer documents this as the #1 CAP theorem mistake."
        ),
        "evidence_keys": ["counter_indicators"],
        "pivot": (
            "Use a CP database (PostgreSQL, MySQL, CockroachDB, Spanner) with ACID guarantees "
            "for all financial, inventory, and ledger data. "
            "If using DynamoDB: enable strongly consistent reads and use transactions for "
            "balance/inventory mutations. "
            "If using Cassandra: use lightweight transactions (LWT) with SERIAL consistency — "
            "but be aware of the performance cost. "
            "Stripe's pattern: all financial writes go through a single Postgres primary with "
            "idempotency keys — never eventually consistent."
        ),
        "citations": [
            "https://github.com/donnemartin/system-design-primer#cap-theorem",
            "https://stripe.com/blog/idempotency",
        ],
    },

    # ── Security ──────────────────────────────────────────────────────────
    {
        "id":             "missing_auth",
        "category":       "SECURITY",
        "triggers":       ["rest", "graphql", "api", "http", "public", "endpoint"],
        "anti_triggers":  ["auth", "jwt", "oauth", "api key", "token", "authentication",
                           "authorization", "iam", "rbac"],
        "team_threshold": 99,
        "risk":           RISK_CRITICAL,
        "title":          "No Authentication / Authorization Mentioned",
        "problem": (
            "APIs with no mention of authentication or authorization are either "
            "unprotected or the auth strategy has not been designed yet. "
            "Unprotected internal APIs become attack vectors when network boundaries "
            "are breached. Missing auth is the #1 cause of API data breaches."
        ),
        "evidence_keys": [],
        "pivot": (
            "Define auth strategy before writing business logic. "
            "For public APIs: OAuth 2.0 + JWT (short-lived access tokens, 15min expiry). "
            "For internal service-to-service: mTLS or signed JWTs with service identity. "
            "For admin APIs: MFA required. "
            "Use a centralized auth service — do not implement auth in each microservice."
        ),
        "citations": [
            "https://owasp.org/www-project-api-security/",
        ],
    },
    {
        "id":             "no_tls",
        "category":       "SECURITY",
        "triggers":       ["rest", "http", "grpc", "api", "websocket", "internal"],
        "anti_triggers":  ["tls", "ssl", "https", "mtls", "encrypted", "certificate"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "No TLS / Encryption in Transit Mentioned",
        "problem": (
            "Services communicating without TLS transmit credentials, tokens, and "
            "user data in plaintext over the network. Internal network traffic is "
            "not inherently safe — lateral movement after a breach exposes all "
            "unencrypted service-to-service traffic. Compliance (HIPAA, PCI-DSS) "
            "mandates encryption in transit."
        ),
        "evidence_keys": [],
        "pivot": (
            "Enforce TLS 1.2+ on all service endpoints, internal and external. "
            "Use mTLS for service-to-service authentication in a zero-trust posture. "
            "Automate certificate rotation (Let's Encrypt, AWS ACM, cert-manager). "
            "Never allow HTTP → only HTTPS with HSTS header set."
        ),
        "citations": [
            "https://owasp.org/www-project-transport-layer-protection-cheat-sheet/",
        ],
    },

    # ── Observability ─────────────────────────────────────────────────────
    {
        "id":             "missing_observability",
        "category":       "OBSERVABILITY",
        "triggers":       ["microservice", "grpc", "rest", "kubernetes", "k8s",
                           "docker", "kafka", "cassandra", "redis"],
        "anti_triggers":  ["monitor", "observ", "tracing", "logging", "alert",
                           "metric", "prometheus", "grafana", "datadog", "cloudwatch",
                           "jaeger", "opentelemetry"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "No Observability Stack Mentioned — Flying Blind in Production",
        "problem": (
            "Distributed systems without metrics, tracing, and structured logging "
            "are impossible to debug in production. When an incident occurs, engineers "
            "spend 80% of their time finding the problem and 20% fixing it. "
            "With proper observability, that ratio inverts. "
            "The average time to detect a production incident without monitoring is "
            "reported by users — not engineers."
        ),
        "evidence_keys": [],
        "pivot": (
            "Implement the three pillars of observability before going to production: "
            "1. METRICS — Prometheus + Grafana (latency p50/p95/p99, error rate, throughput). "
            "2. TRACING — OpenTelemetry + Jaeger/Tempo (distributed request tracing). "
            "3. LOGGING — Structured JSON logs → ELK/Loki (searchable, correlated by trace ID). "
            "Set alerts on error rate > 1% and latency p99 > SLA threshold. "
            "Without these, you will learn about incidents from users, not dashboards."
        ),
        "citations": [
            "https://netflixtechblog.com/tagged/observability",
            "https://opentelemetry.io/docs/concepts/observability-primer/",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY C — TEAM MATURITY RISKS
    # High scale + inexperienced team combinations that are deceptively risky.
    # Inspired by the system-design-primer's section on team operational readiness
    # and the real-world gap between architectural correctness and operational reality.
    # ══════════════════════════════════════════════════════════════════════

    {
        "id":             "high_scale_new_team",
        "category":       "OPERATIONAL",
        "triggers":       ["new team", "new engineer", "greenfield", "first time",
                           "just started", "starting out", "brand new",
                           "100k", "100,000", "500k", "500,000", "1m events",
                           "million events", "event-driven", "event driven", "eda"],
        "anti_triggers":  ["experienced", "sre", "platform team", "runbook",
                           "on-call", "oncall", "incident response", "chaos engineering"],
        "team_threshold": 99,
        "risk":           RISK_CRITICAL,
        "title":          "High Event Volume + New Team — Operational Collapse Risk",
        "problem": (
            "A new team handling 100k+ events/sec faces immediate operational risks "
            "that go far beyond architecture correctness. "
            "At 100,000 events/sec, a 10-minute outage creates a backlog of 60 million "
            "events. Without established runbooks, on-call rotations, and incident "
            "response patterns, that backlog causes cascading failures as downstream "
            "services attempt to catch up simultaneously. "
            "New teams also lack shared domain knowledge on complex EDA patterns: "
            "event sourcing, CQRS, dead-letter queue (DLQ) management, schema evolution, "
            "and partition rebalancing — all of which become critical under this load. "
            "The system-design-primer identifies team operational maturity as a prerequisite "
            "for high-throughput event-driven systems, not an afterthought."
        ),
        "evidence_keys": ["negative_side_effects", "counter_indicators"],
        "pivot": (
            "Three immediate actions before going to production at this scale: "
            "1. RUNBOOKS FIRST — Document incident response for every known failure mode "
            "(broker down, consumer lag spike, DLQ overflow, partition rebalance) before "
            "the first on-call rotation begins. "
            "2. START LOWER — Prove the architecture at 1k events/sec for 4 weeks. "
            "Instrument consumer lag, DLQ depth, and partition offset metrics. "
            "Scale to 10k, then 100k only after the team has handled at least 3 real incidents. "
            "3. MANAGED INFRASTRUCTURE — At this scale with a new team, use a fully managed "
            "broker (Confluent Cloud, AWS MSK, GCP Pub/Sub) not self-managed Kafka/Redpanda. "
            "The SRE overhead of broker management will consume the entire team's capacity "
            "during the first 6 months."
        ),
        "citations": [
            "https://github.com/donnemartin/system-design-primer#event-driven-architecture",
            "https://discord.com/blog/how-discord-stores-trillions-of-messages",
            "https://github.com/ashishps1/awesome-system-design-resources",
        ],
    },
    {
        "id":             "missing_dlq",
        "category":       "DESIGN",
        "triggers":       ["event-driven", "event driven", "eda", "kafka", "sqs", "pubsub",
                           "rabbitmq", "kinesis", "nats", "event", "queue", "consumer",
                           "message", "async"],
        "anti_triggers":  ["dead letter", "dlq", "dead-letter", "poison message",
                           "failed event", "error queue"],
        "team_threshold": 99,
        "risk":           RISK_CRITICAL,
        "title":          "No Dead-Letter Queue (DLQ) — Poison Messages Will Halt Consumers",
        "problem": (
            "Event-driven systems without a dead-letter queue will stall permanently "
            "when a malformed, unparseable, or schema-mismatched event enters the stream. "
            "Without a DLQ, the consumer retries the poison message indefinitely, "
            "blocking all subsequent events in that partition or queue. "
            "At 100k events/sec this means a single bad event stops processing "
            "6 million events per minute within seconds of the failure. "
            "This is one of the most common and most severe EDA operational failures "
            "documented in production post-mortems."
        ),
        "evidence_keys": [],
        "pivot": (
            "Add a dead-letter queue to every consumer in your event pipeline: "
            "AWS SQS: enable DLQ on every queue with maxReceiveCount=3. "
            "Kafka: use a separate dead-letter topic (e.g. topic.DLT) with a DLQ handler service. "
            "Alert on DLQ depth > 0 — any message in the DLQ is a production incident. "
            "Build a DLQ replay mechanism so engineers can reprocess fixed events. "
            "Log the full event payload, stack trace, and consumer offset on DLQ insertion."
        ),
        "citations": [
            "https://aws.amazon.com/blogs/compute/using-amazon-sqs-dead-letter-queues/",
            "https://github.com/donnemartin/system-design-primer#asynchronism",
            "https://github.com/ashishps1/awesome-system-design-resources",
        ],
    },
    {
        "id":             "missing_backpressure",
        "category":       "DESIGN",
        "triggers":       ["event-driven", "event driven", "eda", "100k", "100,000",
                           "500k", "high throughput", "high volume", "kafka", "consumer",
                           "stream", "pipeline", "async", "queue"],
        "anti_triggers":  ["backpressure", "back pressure", "consumer lag", "lag monitor",
                           "flow control", "throttle consumer", "pause consumer"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "No Backpressure Strategy — Consumer Lag Cascade Risk at High Volume",
        "problem": (
            "Event-driven systems at high throughput (100k+ events/sec) without backpressure "
            "controls allow consumer lag to grow unbounded during slowdowns. "
            "When a downstream dependency (database, external API) slows down, "
            "consumers fall behind. Without backpressure, the lag compounds: "
            "at 100k events/sec, 5 minutes of consumer slowdown creates a 30-million "
            "event backlog. When the downstream recovers, all consumers attempt to "
            "catch up simultaneously, causing a thundering herd that re-collapses "
            "the downstream service. "
            "This pattern is well-documented in the system-design-primer's section on "
            "async processing and is one of the top causes of EDA production incidents."
        ),
        "evidence_keys": [],
        "pivot": (
            "Implement backpressure at every consumer: "
            "1. MONITOR LAG — Alert when consumer lag exceeds 60-second equivalent "
            "(e.g. 6 million events at 100k/sec). "
            "2. BOUNDED CONCURRENCY — Limit consumer thread pool size so a slow downstream "
            "slows the consumer gracefully rather than exhausting resources. "
            "3. ADAPTIVE RATE LIMITING — Reduce consumer fetch rate when downstream p99 "
            "latency exceeds threshold. "
            "4. CIRCUIT BREAKER ON DOWNSTREAM — Stop consuming if the downstream is returning "
            "errors above threshold; let lag build rather than cause a thundering herd. "
            "Kafka: use max.poll.records + pause()/resume() on partitions for flow control."
        ),
        "citations": [
            "https://github.com/donnemartin/system-design-primer#asynchronism",
            "https://github.com/ashishps1/awesome-system-design-resources",
        ],
    },
    {
        "id":             "missing_oncall_runbook",
        "category":       "OBSERVABILITY",
        "triggers":       ["new team", "new engineer", "greenfield", "event-driven",
                           "event driven", "microservice", "kubernetes", "kafka",
                           "100k", "100,000", "high throughput"],
        "anti_triggers":  ["runbook", "on-call", "oncall", "incident response",
                           "playbook", "sre", "postmortem", "game day"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "No On-Call Runbooks — Team Will Learn Incident Response Under Fire",
        "problem": (
            "Systems going to production without documented on-call runbooks force "
            "engineers to debug and improvise during live incidents under maximum pressure. "
            "Netflix's Chaos Engineering programme was built specifically because they "
            "discovered their teams did not know how to respond to failures until those "
            "failures happened in production. "
            "For new teams at high scale, the first production incident without runbooks "
            "typically takes 3–5x longer to resolve than it should — and the extended "
            "downtime compounds the event backlog problem dramatically."
        ),
        "evidence_keys": ["positive_outcomes"],
        "pivot": (
            "Before going to production, write runbooks for every known failure mode: "
            "1. FAILURE SCENARIOS — broker down, consumer group rebalance, DLQ overflow, "
            "database connection pool exhaustion, downstream timeout cascade. "
            "2. RUNBOOK STRUCTURE — detection signal (which alert fires), "
            "immediate mitigation (what to do in first 5 minutes), "
            "root cause investigation steps, escalation path. "
            "3. GAME DAYS — run a scheduled failure drill before launch. "
            "Kill a broker in staging. Watch the team respond. Fix the gaps. "
            "Netflix's Chaos Monkey exists because they learned this lesson expensively. "
            "4. ON-CALL ROTATION — defined before launch, not after first incident."
        ),
        "citations": [
            "https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116",
            "https://github.com/donnemartin/system-design-primer#availability-vs-consistency",
            "https://github.com/ashishps1/awesome-system-design-resources",
        ],
    },
    # ══════════════════════════════════════════════════════════════════════
    # CATEGORY D — ML INFRASTRUCTURE RISKS
    # Sourced from Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies
    # Covers production ML failure modes: skew, versioning, feedback loops,
    # evaluation gaps, and inference routing mistakes.
    # ══════════════════════════════════════════════════════════════════════

    {
        "id":             "training_serving_skew",
        "category":       "DESIGN",
        "triggers":       ["ml", "model", "inference", "prediction", "machine learning",
                           "train", "feature", "embedding", "llm", "neural", "sklearn",
                           "pytorch", "tensorflow", "xgboost", "recommend"],
        "anti_triggers":  ["feature store", "feast", "tecton", "hopsworks",
                           "feature pipeline", "point-in-time", "skew detection",
                           "online offline parity", "feature versioning"],
        "team_threshold": 99,
        "risk":           RISK_CRITICAL,
        "title":          "No Feature Store — Training-Serving Skew Risk",
        "problem": (
            "Without a centralised feature store, features are computed differently "
            "at training time (batch, from historical data) vs serving time (real-time, "
            "from live data). This training-serving skew causes silent model accuracy "
            "degradation in production that is invisible in offline metrics. "
            "Airbnb, DoorDash, and Uber all documented this as their #1 ML infrastructure "
            "failure mode. A model can pass all offline tests and fail silently in "
            "production for weeks before anyone notices the accuracy has collapsed."
        ),
        "evidence_keys": ["positive_outcomes", "negative_side_effects"],
        "pivot": (
            "Implement a feature store (Feast, Tecton, Hopsworks, or custom Redis-backed) "
            "that serves identical features at training and inference time. "
            "Key requirements: "
            "1. Point-in-time correct joins for training — never use future data. "
            "2. Online store (Redis/DynamoDB) for low-latency serving. "
            "3. Offline store (S3/BigQuery) for training data retrieval. "
            "4. Automated skew detection — alert when online/offline distributions diverge >5%. "
            "Airbnb reported 15% prediction quality improvement after unifying feature pipelines."
        ),
        "citations": [
            "https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
            "https://www.uber.com/blog/michelangelo-machine-learning-platform/",
            "https://docs.feast.dev/",
        ],
    },
    {
        "id":             "no_model_versioning",
        "category":       "OPERATIONAL",
        "triggers":       ["ml", "model", "deploy", "inference", "prediction",
                           "machine learning", "pytorch", "tensorflow", "serving",
                           "production model", "model server"],
        "anti_triggers":  ["shadow", "canary", "rollback", "model registry",
                           "mlflow", "wandb", "model version", "a/b model",
                           "blue green model", "champion challenger"],
        "team_threshold": 99,
        "risk":           RISK_CRITICAL,
        "title":          "No Model Versioning or Rollback — Bad Model Has No Recovery Path",
        "problem": (
            "Deploying ML models without versioning, shadow testing, or automated rollback "
            "means a bad model deployment has no fast recovery path. "
            "Unlike a software bug where you revert a commit, a model regression is often "
            "silent — the model produces predictions, just bad ones. "
            "Without a model registry, you cannot reproduce the previous model artifact. "
            "Without shadow deployment, you have no pre-production signal that the new model "
            "is worse. Netflix, Airbnb, and LinkedIn all document model rollback as a "
            "non-negotiable prerequisite before any model reaches production traffic."
        ),
        "evidence_keys": ["positive_outcomes", "negative_side_effects"],
        "pivot": (
            "Implement three controls before any model goes to production: "
            "1. MODEL REGISTRY — store every trained model artifact with metadata "
            "(metrics, training data version, feature schema). Use MLflow, W&B, or SageMaker Registry. "
            "2. SHADOW DEPLOYMENT — run new model in parallel for 24–48h, log predictions, "
            "compare against current model before switching any traffic. "
            "3. AUTOMATED ROLLBACK — if online metrics (CTR, conversion, latency) drop >X% "
            "within 1 hour of rollout, automatically revert to previous model version. "
            "Netflix's model deployment pipeline blocks promotion if shadow metrics are worse."
        ),
        "citations": [
            "https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
            "https://netflixtechblog.com/tagged/machine-learning",
        ],
    },
    {
        "id":             "recommender_feedback_loop",
        "category":       "DESIGN",
        "triggers":       ["recommend", "recommender", "ranking", "personalisation",
                           "personalization", "collaborative filtering", "content-based",
                           "click", "feed", "suggestion", "discovery"],
        "anti_triggers":  ["exploration", "diversity", "counterfactual", "epsilon greedy",
                           "thompson sampling", "explore exploit", "exposure correction",
                           "feedback loop", "popularity bias"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "No Feedback Loop Protection — Recommender Will Amplify Popularity Bias",
        "problem": (
            "Recommender systems without explicit feedback loop controls enter a "
            "self-reinforcing cycle: the model recommends popular items, users click them "
            "(because they are shown), the model learns they are better, recommends them more. "
            "Long-tail items starve. New items never get exposure. "
            "The model optimises click-through rate while long-term user satisfaction (hours "
            "watched, repeat visits, subscription retention) declines. "
            "Netflix, YouTube, and Airbnb all document this as one of the hardest production "
            "ML problems — the model appears to improve on offline metrics while the product "
            "slowly degrades."
        ),
        "evidence_keys": ["positive_outcomes", "negative_side_effects"],
        "pivot": (
            "Add three controls to break the feedback loop: "
            "1. EXPLORATION BUDGET — reserve 5–10% of recommendations for items outside the "
            "model's current top-k. Forces exposure to long-tail and new items. "
            "2. COUNTERFACTUAL LOGGING — log what was NOT shown alongside what was, "
            "enabling unbiased offline evaluation and debias training. "
            "3. SEPARATE METRICS — track short-term engagement (clicks) separately from "
            "long-term satisfaction (return rate, watch time, subscription renewal). "
            "Optimise the model on the long-term metric, not the short-term proxy. "
            "Netflix explicitly separates play rate from satisfaction rating in ranking."
        ),
        "citations": [
            "https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
            "https://netflixtechblog.com/netflix-recommendations-beyond-the-5-stars-part-1-55838468f429",
        ],
    },
    {
        "id":             "batch_inference_realtime_sla",
        "category":       "DESIGN",
        "triggers":       ["batch inference", "batch prediction", "offline inference",
                           "scheduled prediction", "precompute", "pre-compute",
                           "nightly batch", "daily batch"],
        "anti_triggers":  ["real-time inference", "online inference", "model server",
                           "triton", "torchserve", "tf serving", "sagemaker endpoint",
                           "latency sla", "p99 latency"],
        "team_threshold": 99,
        "risk":           RISK_WARNING,
        "title":          "Batch Inference for a Real-Time Use Case — Staleness Will Cause Accuracy Degradation",
        "problem": (
            "Batch inference (pre-computing predictions nightly or hourly) is inappropriate "
            "for use cases where the prediction context changes within the serving window. "
            "A ride pricing model pre-computed hourly fails during sudden demand spikes. "
            "A fraud model pre-computed nightly misses intra-day fraud pattern shifts. "
            "A product recommendation pre-computed daily cannot respond to items a user "
            "just added to their cart. "
            "Uber, Airbnb, and LinkedIn all document batch-vs-realtime routing as a "
            "fundamental ML architecture decision that is expensive to reverse after launch."
        ),
        "evidence_keys": ["negative_side_effects", "counter_indicators"],
        "pivot": (
            "Determine the required feature freshness window first, then choose inference mode: "
            "BATCH is correct when: predictions change hourly or slower, context is user-level "
            "not session-level, low-latency serving is not required (<50ms SLA not needed). "
            "REAL-TIME is required when: predictions depend on current session, live inventory, "
            "real-time pricing, or fraud signals from the last 60 seconds. "
            "HYBRID (Uber's approach): batch for slow-moving features (user history, demographics) "
            "served from Redis cache + real-time for fast-moving features (current location, "
            "live demand) merged at inference time. Reduces real-time compute by 70%+ "
            "while maintaining freshness where it matters."
        ),
        "citations": [
            "https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
            "https://www.uber.com/blog/michelangelo-machine-learning-platform/",
        ],
    },
]
# ---------------------------------------------------------------------------
def _has_anti_trigger(rule: dict, text_lower: str, keywords: list[str]) -> bool:
    """
    Return True if any anti-trigger is present in the RAW TEXT — meaning the design
    issue is already addressed.

    IMPORTANT: We check raw text only, NOT keywords. Keywords are extracted without
    negation context — "no circuit breaker" would add "circuit breaker" to keywords,
    wrongly suppressing the rule. Raw text preserves the "no" prefix.
    """
    for at in rule.get("anti_triggers", []):
        if at in text_lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Critic Engine
# ---------------------------------------------------------------------------
class CriticEngine:
    def __init__(self, graph: Any) -> None:
        self.graph = graph

    # ── Main entry point ─────────────────────────────────────────────────────
    def critique(self, arch_input: ArchitectureInput) -> CritiqueReport:
        items: list[CritiqueItem] = []
        overall_risks = [RISK_OK]

        text_lower = arch_input.raw_description.lower()
        kw_lower   = [k.lower() for k in arch_input.stack_keywords]

        for rule in _RULES:
            matched = any(t in text_lower or t in kw_lower for t in rule["triggers"])
            if not matched:
                continue
            if _has_anti_trigger(rule, text_lower, kw_lower):
                continue
            if rule["team_threshold"] < 99:
                if arch_input.team_size >= rule["team_threshold"]:
                    continue

            graph_hits = self.graph.query_by_stack(
                rule["triggers"], domain_filter=arch_input.domain
            )

            evidence:  list[str] = []
            citations: list[str] = list(rule.get("citations", []))
            score = 1.0

            for hit in graph_hits[:3]:
                for key in rule.get("evidence_keys", []):
                    vals = hit.get(key, [])
                    if isinstance(vals, list):
                        evidence.extend(vals[:2])
                src = hit.get("source_url") or hit.get("url", "")
                if src and src not in citations:
                    citations.append(src)
                score = min(score, _scale_match_score(hit, arch_input.team_size))

            if not citations:
                citations = ["[Source not yet in graph — submit via GitHub Issues]"]

            item = CritiqueItem(
                risk_level        = rule["risk"],
                category          = rule["category"],
                title             = rule["title"],
                problem           = rule["problem"],
                evidence          = evidence[:4],
                pivot             = rule["pivot"],
                citations         = citations,
                scale_match_score = score if score < 1.0 else 1.0,
                technique_id      = rule["id"],
            )
            items.append(item)
            overall_risks.append(item.risk_level)

        risk_order = [RISK_OK, RISK_INFO, RISK_WARNING, RISK_CRITICAL]
        overall    = max(overall_risks, key=lambda r: risk_order.index(r))

        blueprint = self._generate_blueprint(arch_input, items)

        return CritiqueReport(
            architecture_summary = arch_input.raw_description[:200],
            team_size    = arch_input.team_size,
            domain       = arch_input.domain,
            items        = items,
            overall_risk = overall,
            blueprint    = blueprint,
        )

    # ── Blueprint generator ───────────────────────────────────────────────────
    def _generate_blueprint(
        self,
        arch: ArchitectureInput,
        issues: list[CritiqueItem],
    ) -> DesignBlueprint:
        """
        Generate a best-design blueprint tailored to this specific architecture.
        Layers are built from what was detected in the description + what was missing.
        """
        tl   = arch.raw_description.lower()
        kws  = arch.stack_keywords
        dom  = arch.domain or "General"
        team = arch.team_size

        # Collect issue IDs to know what was missing
        missing = {i.technique_id for i in issues}

        layers:       list[BlueprintLayer] = []
        checklist:    list[str] = []
        anti_patterns:list[str] = []
        citations:    list[str] = []

        # ── Client / Entry Layer ──────────────────────────────────────────────
        if any(w in tl for w in ["react", "vue", "angular", "frontend", "web", "static"]):
            has_cdn = "missing_cdn" not in missing
            layers.append(BlueprintLayer(
                layer     = "Client / CDN Layer",
                component = "React/Vue SPA served via CloudFront/Cloudflare CDN"
                            if has_cdn else
                            "React/Vue SPA → ⚠️ ADD CDN (CloudFront/Cloudflare)",
                why       = "CDN reduces origin load 80–90% and cuts global latency to <50ms",
                source    = "system-design-primer (donnemartin)",
            ))
            if not has_cdn:
                checklist.append("Add CDN (CloudFront / Cloudflare) for all static assets")
                citations.append("https://github.com/donnemartin/system-design-primer#content-delivery-network")

        # ── API / Gateway Layer ───────────────────────────────────────────────
        has_lb      = "missing_load_balancer" not in missing
        has_ratelim = "missing_rate_limiting" not in missing
        has_auth    = "missing_auth" not in missing
        has_tls     = "missing_tls" not in missing

        api_comp = "nginx/ALB load balancer → API Gateway (rate limiting, auth, TLS) → Services"
        api_gaps = []
        if not has_lb:      api_gaps.append("⚠️ add load balancer")
        if not has_ratelim: api_gaps.append("⚠️ add rate limiting")
        if not has_auth:    api_gaps.append("⚠️ add OAuth2/JWT auth")
        if not has_tls:     api_gaps.append("⚠️ enforce TLS")

        if any(w in tl for w in ["rest", "graphql", "grpc", "api", "http", "microservice"]):
            layers.append(BlueprintLayer(
                layer     = "API / Gateway Layer",
                component = api_comp + (" [" + ", ".join(api_gaps) + "]" if api_gaps else " ✅"),
                why       = "Single entry point for auth, rate limiting, TLS termination, and routing",
                source    = "Netflix API Resilience Pattern",
            ))
            if not has_lb:
                checklist.append("Add load balancer (nginx Ingress on K8s, or AWS ALB) with health checks")
                anti_patterns.append("Single API instance with no load balancer — one crash = full downtime")
            if not has_ratelim:
                checklist.append("Implement rate limiting at gateway (100 req/min per API key, return 429)")
                anti_patterns.append("Unprotected public API — single misbehaving client can exhaust all connections")
            if not has_auth:
                checklist.append("Add OAuth2 + JWT authentication (15-min access token, refresh token rotation)")
                anti_patterns.append("No authentication on API endpoints — #1 cause of API data breaches (OWASP)")
            if not has_tls:
                checklist.append("Enforce HTTPS everywhere — HSTS header, auto-renew TLS certs via cert-manager")
                anti_patterns.append("HTTP in transit — credentials and tokens exposed to network interception")

        # ── Service / Business Logic Layer ────────────────────────────────────
        has_cb    = "missing_circuit_breaker" not in missing
        has_retry = "missing_retry_timeout" not in missing

        if any(w in tl for w in ["microservice", "service", "kubernetes", "k8s"]):
            svc_comp = "Microservices on Kubernetes"
            svc_gaps = []
            if not has_cb:    svc_gaps.append("⚠️ add circuit breaker")
            if not has_retry: svc_gaps.append("⚠️ add retry+timeout")
            layers.append(BlueprintLayer(
                layer     = "Service Layer",
                component = svc_comp + (" [" + ", ".join(svc_gaps) + "]" if svc_gaps else
                            " + circuit breakers + retry/timeout ✅"),
                why       = "Circuit breakers prevent cascading failure; retry+timeout bound tail latency",
                source    = "Netflix Hystrix Pattern (600+ microservices)",
            ))
            if not has_cb:
                checklist.append("Add circuit breakers on all synchronous service calls (open after 5 failures/10s)")
                anti_patterns.append("Microservices without circuit breakers — one slow service takes down the entire call chain")
                citations.append("https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d")
            if not has_retry:
                checklist.append("Set explicit timeout on every outbound call (p99 latency × 3). Exponential backoff with jitter, max 3 retries.")
                anti_patterns.append("No timeout on downstream calls — hanging connections accumulate during partial failures")

        # ── Messaging / Event Layer ───────────────────────────────────────────
        has_dlq = "missing_dlq" not in missing
        has_bp  = "missing_backpressure" not in missing

        if any(w in tl for w in ["kafka", "sqs", "event", "queue", "pubsub", "async", "rabbitmq"]):
            broker = "Confluent Cloud / AWS MSK" if team < 5 else "Kafka (self-managed if team ≥ 5)"
            msg_gaps = []
            if not has_dlq: msg_gaps.append("⚠️ add DLQ")
            if not has_bp:  msg_gaps.append("⚠️ add backpressure")
            layers.append(BlueprintLayer(
                layer     = "Messaging / Event Layer",
                component = f"{broker} + Dead-Letter Queue + consumer lag monitoring"
                            + (" [" + ", ".join(msg_gaps) + "]" if msg_gaps else " ✅"),
                why       = "DLQ prevents poison messages stalling all consumers; lag monitoring catches cascade early",
                source    = "Discord Kafka Elimination + Tesla Edge Batching Patterns",
            ))
            if not has_dlq:
                checklist.append("Add DLQ to every consumer. Alert on DLQ depth > 0. Build replay mechanism.")
                anti_patterns.append("No DLQ — one malformed event stalls entire partition (6M events/min at 100k/sec)")
            if not has_bp:
                checklist.append("Implement backpressure: monitor consumer lag, bound thread pool, pause/resume on downstream pressure")
                anti_patterns.append("No backpressure — consumer lag compounds into thundering herd during downstream recovery")

        # ── Data Layer ────────────────────────────────────────────────────────
        has_cache   = "no_caching_layer" not in missing
        has_replica = "single_point_of_failure_db" not in missing
        has_cap     = "cap_wrong_consistency" not in missing

        db_detected = any(w in tl for w in ["postgres", "mysql", "mongodb", "cassandra",
                                             "dynamodb", "sqlite", "database", "db"])
        if db_detected:
            db_gaps = []
            if not has_replica: db_gaps.append("⚠️ add read replica / failover")
            if not has_cache:   db_gaps.append("⚠️ add Redis cache")
            if dom == "Finance" and not has_cap:
                db_gaps.append("⚠️ use CP/ACID database for financial data")

            layers.append(BlueprintLayer(
                layer     = "Data Layer",
                component = "PostgreSQL (multi-AZ primary + read replica) + Redis cache"
                            + (" [" + ", ".join(db_gaps) + "]" if db_gaps else " ✅"),
                why       = "Multi-AZ gives <30s failover; Redis cache targets 80%+ hit rate before DB scales",
                source    = "system-design-primer read replica + Discord ScyllaDB patterns",
            ))
            if not has_replica:
                checklist.append("Add read replica with automated failover (RDS Multi-AZ, Aurora, or Cloud SQL HA)")
                anti_patterns.append("Single database instance — disk failure or bad migration = 15–60 min downtime with no automatic recovery")
            if not has_cache:
                checklist.append("Add Redis cache (cache-aside pattern). Target 80%+ hit rate. TTL ≥ 1s for stable reads.")
                anti_patterns.append("All reads hitting database directly — hits hard scalability wall at moderate traffic")
            if dom == "Finance" and not has_cap:
                checklist.append("Use PostgreSQL/MySQL with ACID transactions for all financial writes — never eventual consistency")
                anti_patterns.append("Eventual consistency (Cassandra/DynamoDB default) on financial data = silent double-charges, negative balances")
                citations.append("https://github.com/donnemartin/system-design-primer#cap-theorem")

        # ── ML Layer (if applicable) ──────────────────────────────────────────
        has_fs  = "training_serving_skew" not in missing
        has_mv  = "no_model_versioning" not in missing

        if any(w in tl for w in ["ml", "model", "train", "inference", "recommend", "feature"]):
            ml_gaps = []
            if not has_fs: ml_gaps.append("⚠️ add feature store")
            if not has_mv: ml_gaps.append("⚠️ add model versioning + shadow deploy")
            layers.append(BlueprintLayer(
                layer     = "ML Infrastructure Layer",
                component = "Feature Store (Feast) + Model Registry (MLflow) + Shadow Deployment"
                            + (" [" + ", ".join(ml_gaps) + "]" if ml_gaps else " ✅"),
                why       = "Feature store prevents training-serving skew; shadow deploy catches regressions before users see them",
                source    = "Uber Michelangelo + Netflix Model Deployment Patterns",
            ))
            if not has_fs:
                checklist.append("Implement feature store (Feast/Tecton): unified online (Redis) + offline (S3) feature access")
                anti_patterns.append("Features computed differently at training vs serving — silent model accuracy collapse in production (Airbnb, DoorDash, Uber all documented this)")
                citations.append("https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies")
            if not has_mv:
                checklist.append("Add model registry (MLflow/W&B). Implement shadow deployment for 24h before any traffic switch. Automated rollback if metrics degrade.")
                anti_patterns.append("Deploying models without versioning — no rollback path when model regresses silently")

        # ── Observability Layer ───────────────────────────────────────────────
        has_obs     = "missing_observability" not in missing
        has_runbook = "missing_oncall_runbook" not in missing

        obs_gaps = []
        if not has_obs:     obs_gaps.append("⚠️ add Prometheus+Grafana+OpenTelemetry")
        if not has_runbook: obs_gaps.append("⚠️ write on-call runbooks")

        layers.append(BlueprintLayer(
            layer     = "Observability Layer",
            component = "Prometheus + Grafana + OpenTelemetry + structured logging (Loki)"
                        + (" [" + ", ".join(obs_gaps) + "]" if obs_gaps else " ✅"),
            why       = "Without metrics+tracing+logging, engineers learn about incidents from users not dashboards",
            source    = "Netflix Simian Army + OpenTelemetry standard",
        ))
        if not has_obs:
            checklist.append("Set up Prometheus (metrics), Grafana (dashboards), OpenTelemetry (tracing), Loki (logs). Alert on error rate >1% and p99 > SLA.")
            anti_patterns.append("No observability — engineers spend 80% of incident time finding the problem instead of fixing it")
            citations.append("https://opentelemetry.io/docs/concepts/observability-primer/")
        if not has_runbook:
            checklist.append("Write runbooks for every known failure mode before go-live. Define on-call rotation. Run a game day in staging.")
            anti_patterns.append("No runbooks — team learns incident response under maximum pressure during a live production failure")
            citations.append("https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116")

        # ── Domain-specific additions ─────────────────────────────────────────
        if dom == "MedTech":
            layers.append(BlueprintLayer(
                layer     = "Edge Safety Layer (MedTech-specific)",
                component = "Air-gapped bedside edge appliance + hardwired fail-safe relay alarms",
                why       = "Patient alarms must fire even during total WAN/LAN outage — FDA SaMD Class II/III requirement",
                source    = "Philips HealthTech IoMT Hub-and-Spoke Pattern",
            ))
            checklist.append("Move alarm logic to local edge appliance. Use hardwired relay for life-critical thresholds. Async batch telemetry upload to cloud.")
            anti_patterns.append("Centralized WebSocket for patient vitals — WAN outage silences all alarms (FDA violation)")
            citations.append("https://innovation.philips.com/blog/iomt-edge-architecture")

        # Deduplicate citations
        seen = set()
        unique_citations = []
        for c in citations:
            if c not in seen:
                seen.add(c)
                unique_citations.append(c)

        # Build title and summary
        domain_label = f"{dom} " if dom != "General" else ""
        title = f"Best Design for {domain_label}Architecture — {team} Engineers"

        if overall_risk := max(
            (i.risk_level for i in issues),
            key=lambda r: [RISK_OK, RISK_INFO, RISK_WARNING, RISK_CRITICAL].index(r),
            default=RISK_OK,
        ):
            pass

        summary = (
            f"Based on your stack and {len(issues)} issue(s) detected, this is the "
            f"recommended target architecture. Each layer addresses a specific failure "
            f"mode documented in production post-mortems from companies at your scale."
            if issues else
            f"Your architecture has no critical issues. This blueprint confirms the "
            f"patterns you already have and highlights what to preserve as you scale."
        )

        return DesignBlueprint(
            title         = title,
            summary       = summary,
            layers        = layers,
            checklist     = checklist,
            anti_patterns = anti_patterns,
            citations     = unique_citations,
        )
