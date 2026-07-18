# ArchGraph AI Comprehensive Report

## WebScale - Failure Scenario
### Input
`microservices architecture, no circuit breakers, 3 engineers`

### Output
```text
======================================================================
  ArchGraph AI — Architecture Critique Report
======================================================================
  Architecture : microservices architecture, no circuit breakers, 3 engineers
  Team Size    : 3 engineers
  Domain       : General
  Overall Risk : WARNING
  Issues found : 5 (0 operational / 3 design / 0 security / 2 observability)
======================================================================

──────────────────────────────────────────────────────────────────────
  🏗  DESIGN ISSUES
──────────────────────────────────────────────────────────────────────

  ⚠️  [WARNING] No Retry / Timeout Strategy — Silent Failure Risk
  Scale Match Score: 0.3/1.0 ← TEAM TOO SMALL

  PROBLEM
  Services that call downstream dependencies without explicit timeouts accumulate hanging connections during partial failures. Without retry logic, transient network errors cause permanent user-visible failures. Without exponential backoff, retry storms during recovery can re-collapse a service that is just coming back online.

  RECOMMENDED FIX
  Set explicit timeouts on every outbound call (recommend: p99 latency × 3). Implement exponential backoff with jitter on retries (max 3 attempts). Use deadline propagation — if the upstream request has 200ms left, do not set a 500ms timeout on the downstream call. Never retry non-idempotent write operations without idempotency keys.

  CITATIONS
   → https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
----------------------------------------------------------------------

  ⚠️  [WARNING] Deep Synchronous Service Chain — Latency Multiplication
  Scale Match Score: 0.3/1.0 ← TEAM TOO SMALL

  PROBLEM
  Synchronous call chains multiply latency: if A calls B calls C calls D, the user-facing latency is A+B+C+D plus network overhead. A chain of 4 services each averaging 50ms produces 200ms+ minimum latency before any business logic runs. Under load, tail latencies compound multiplicatively. This is a structural design problem — adding capacity does not fix it.

  RECOMMENDED FIX
  Identify which downstream calls can be made async via event queue. Use fan-out pattern for independent downstream calls (run in parallel). Cache stable downstream data at the edge service. Reserve synchronous chains for operations where the result is needed immediately by the user (< 3 service hops recommended). Consider event sourcing / CQRS for write paths that trigger multiple downstream effects.

  CITATIONS
   → https://engineering.fb.com/2020/05/07/data-infrastructure/messenger/
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
   → https://anthropic.com/research/building-effective-agents
----------------------------------------------------------------------

  ⚠️  [WARNING] No Load Balancer Mentioned — Single Point of Failure on Entry
  Scale Match Score: 0.2/1.0 ← TEAM TOO SMALL

  PROBLEM
  Systems with multiple service instances or containers but no load balancer have no automatic traffic distribution or health-check-based failover. A single failed instance continues to receive traffic until manually removed. The system-design-primer identifies load balancing as a prerequisite for any horizontally-scaled architecture — without it, scaling adds capacity but not reliability.

  RECOMMENDED FIX
  Add a load balancer at every tier boundary. For Kubernetes: use an Ingress controller (nginx-ingress, Traefik) or a service mesh (Istio, Linkerd) for internal load balancing. For cloud: AWS ALB/NLB, GCP Load Balancer, or Azure Application Gateway. Configure health checks so failed pods are removed from rotation automatically. Use Layer 7 load balancing for HTTP — enables path-based routing and sticky sessions.

  CITATIONS
   → https://github.com/donnemartin/system-design-primer#load-balancer
   → https://github.com/ashishps1/awesome-system-design-resources
   → https://discord.com/blog/how-discord-stores-trillions-of-messages
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
   → https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116
----------------------------------------------------------------------

──────────────────────────────────────────────────────────────────────
  📊 OBSERVABILITY GAPS
──────────────────────────────────────────────────────────────────────

  ⚠️  [WARNING] No Observability Stack Mentioned — Flying Blind in Production
  Scale Match Score: 0.3/1.0 ← TEAM TOO SMALL

  PROBLEM
  Distributed systems without metrics, tracing, and structured logging are impossible to debug in production. When an incident occurs, engineers spend 80% of their time finding the problem and 20% fixing it. With proper observability, that ratio inverts. The average time to detect a production incident without monitoring is reported by users — not engineers.

  RECOMMENDED FIX
  Implement the three pillars of observability before going to production: 1. METRICS — Prometheus + Grafana (latency p50/p95/p99, error rate, throughput). 2. TRACING — OpenTelemetry + Jaeger/Tempo (distributed request tracing). 3. LOGGING — Structured JSON logs → ELK/Loki (searchable, correlated by trace ID). Set alerts on error rate > 1% and latency p99 > SLA threshold. Without these, you will learn about incidents from users, not dashboards.

  CITATIONS
   → https://netflixtechblog.com/tagged/observability
   → https://opentelemetry.io/docs/concepts/observability-primer/
   → https://discord.com/blog/how-discord-stores-trillions-of-messages
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
----------------------------------------------------------------------

  ⚠️  [WARNING] No On-Call Runbooks — Team Will Learn Incident Response Under Fire
  Scale Match Score: 0.3/1.0 ← TEAM TOO SMALL

  PROBLEM
  Systems going to production without documented on-call runbooks force engineers to debug and improvise during live incidents under maximum pressure. Netflix's Chaos Engineering programme was built specifically because they discovered their teams did not know how to respond to failures until those failures happened in production. For new teams at high scale, the first production incident without runbooks typically takes 3–5x longer to resolve than it should — and the extended downtime compounds the event backlog problem dramatically.

  ENGINEERING SCARS (from production post-mortems)
   • Eliminated Kafka broker management overhead for a sub-10-engineer team
   • Reduced end-to-end message delivery latency below 50ms p99
   • Prevented cascading failure propagation across 600+ microservices
   • Fallback responses kept user experience degraded-but-functional during partial outages

  RECOMMENDED FIX
  Before going to production, write runbooks for every known failure mode: 1. FAILURE SCENARIOS — broker down, consumer group rebalance, DLQ overflow, database connection pool exhaustion, downstream timeout cascade. 2. RUNBOOK STRUCTURE — detection signal (which alert fires), immediate mitigation (what to do in first 5 minutes), root cause investigation steps, escalation path. 3. GAME DAYS — run a scheduled failure drill before launch. Kill a broker in staging. Watch the team respond. Fix the gaps. Netflix's Chaos Monkey exists because they learned this lesson expensively. 4. ON-CALL ROTATION — defined before launch, not after first incident.

  CITATIONS
   → https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116
   → https://github.com/donnemartin/system-design-primer#availability-vs-consistency
   → https://github.com/ashishps1/awesome-system-design-resources
   → https://discord.com/blog/how-discord-stores-trillions-of-messages
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
   → https://tesla.com/blog/engineering-telemetry
----------------------------------------------------------------------

======================================================================
  ArchGraph AI — Recommended Best Design
======================================================================
  Best Design for Architecture — 3 Engineers

  Based on your stack and 5 issue(s) detected, this is the recommended target architecture. Each layer addresses a specific failure mode documented in production post-mortems from companies at your scale.

──────────────────────────────────────────────────────────────────────
  🏗  ARCHITECTURE LAYERS
──────────────────────────────────────────────────────────────────────

  ┌─ API / Gateway Layer
  │  Component : nginx/ALB load balancer → API Gateway (rate limiting, auth, TLS) → Services [⚠️ add load balancer]
  │  Why       : Single entry point for auth, rate limiting, TLS termination, and routing
  │  Pattern   : Netflix API Resilience Pattern
  │
  ┌─ Service Layer
  │  Component : Microservices on Kubernetes [⚠️ add retry+timeout]
  │  Why       : Circuit breakers prevent cascading failure; retry+timeout bound tail latency
  │  Pattern   : Netflix Hystrix Pattern (600+ microservices)
  │
  ┌─ Observability Layer
  │  Component : Prometheus + Grafana + OpenTelemetry + structured logging (Loki) [⚠️ add Prometheus+Grafana+OpenTelemetry, ⚠️ write on-call runbooks]
  │  Why       : Without metrics+tracing+logging, engineers learn about incidents from users not dashboards
  │  Pattern   : Netflix Simian Army + OpenTelemetry standard
  │

──────────────────────────────────────────────────────────────────────
  ✅ IMPLEMENTATION CHECKLIST
──────────────────────────────────────────────────────────────────────

  01. Add load balancer (nginx Ingress on K8s, or AWS ALB) with health checks
  02. Set explicit timeout on every outbound call (p99 latency × 3). Exponential backoff with jitter, max 3 retries.
  03. Set up Prometheus (metrics), Grafana (dashboards), OpenTelemetry (tracing), Loki (logs). Alert on error rate >1% and p99 > SLA.
  04. Write runbooks for every known failure mode before go-live. Define on-call rotation. Run a game day in staging.

──────────────────────────────────────────────────────────────────────
  🚫 WHAT NOT TO DO (from post-mortems)
──────────────────────────────────────────────────────────────────────

   ✗ Single API instance with no load balancer — one crash = full downtime
   ✗ No timeout on downstream calls — hanging connections accumulate during partial failures
   ✗ No observability — engineers spend 80% of incident time finding the problem instead of fixing it
   ✗ No runbooks — team learns incident response under maximum pressure during a live production failure

──────────────────────────────────────────────────────────────────────
  📚 CITATIONS
──────────────────────────────────────────────────────────────────────

   → https://opentelemetry.io/docs/concepts/observability-primer/
   → https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116
======================================================================
```

---

## WebScale - Success Scenario
### Input
`stateless microservices, auto-scaling, 15 engineers`

### Output
```text
======================================================================
  ArchGraph AI — Architecture Critique Report
======================================================================
  Architecture : stateless microservices, auto-scaling, 15 engineers
  Team Size    : 15 engineers
  Domain       : General
  Overall Risk : CRITICAL
  Issues found : 6 (0 operational / 4 design / 0 security / 2 observability)
======================================================================

──────────────────────────────────────────────────────────────────────
  🏗  DESIGN ISSUES
──────────────────────────────────────────────────────────────────────

  ❌ [CRITICAL] No Circuit Breaker — Cascading Failure Risk

  PROBLEM
  Microservice architectures without circuit breakers propagate failures across service boundaries. A single slow downstream service causes thread pool exhaustion upstream, taking down the entire call chain. Netflix experienced cascading failures across 600+ microservices before implementing Hystrix circuit breakers.

  ENGINEERING SCARS (from production post-mortems)
   • Prevented cascading failure propagation across 600+ microservices
   • Fallback responses kept user experience degraded-but-functional during partial outages
   • Hystrix thread pools added 10–15ms latency overhead per service hop
   • Fallback logic must be explicitly maintained — silent staleness risk

  RECOMMENDED FIX
  Implement circuit breakers on all synchronous inter-service calls. Use Netflix Hystrix pattern: open circuit after 5 failures in 10s, return fallback response, half-open after 30s to probe recovery. Resilience4j (Java), resilience (Python), or Envoy sidecar all work.

  CITATIONS
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
----------------------------------------------------------------------

  ⚠️  [WARNING] No Retry / Timeout Strategy — Silent Failure Risk

  PROBLEM
  Services that call downstream dependencies without explicit timeouts accumulate hanging connections during partial failures. Without retry logic, transient network errors cause permanent user-visible failures. Without exponential backoff, retry storms during recovery can re-collapse a service that is just coming back online.

  RECOMMENDED FIX
  Set explicit timeouts on every outbound call (recommend: p99 latency × 3). Implement exponential backoff with jitter on retries (max 3 attempts). Use deadline propagation — if the upstream request has 200ms left, do not set a 500ms timeout on the downstream call. Never retry non-idempotent write operations without idempotency keys.

  CITATIONS
   → https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
----------------------------------------------------------------------

  ⚠️  [WARNING] Deep Synchronous Service Chain — Latency Multiplication

  PROBLEM
  Synchronous call chains multiply latency: if A calls B calls C calls D, the user-facing latency is A+B+C+D plus network overhead. A chain of 4 services each averaging 50ms produces 200ms+ minimum latency before any business logic runs. Under load, tail latencies compound multiplicatively. This is a structural design problem — adding capacity does not fix it.

  RECOMMENDED FIX
  Identify which downstream calls can be made async via event queue. Use fan-out pattern for independent downstream calls (run in parallel). Cache stable downstream data at the edge service. Reserve synchronous chains for operations where the result is needed immediately by the user (< 3 service hops recommended). Consider event sourcing / CQRS for write paths that trigger multiple downstream effects.

  CITATIONS
   → https://engineering.fb.com/2020/05/07/data-infrastructure/messenger/
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
   → https://anthropic.com/research/building-effective-agents
----------------------------------------------------------------------

  ⚠️  [WARNING] No Load Balancer Mentioned — Single Point of Failure on Entry

  PROBLEM
  Systems with multiple service instances or containers but no load balancer have no automatic traffic distribution or health-check-based failover. A single failed instance continues to receive traffic until manually removed. The system-design-primer identifies load balancing as a prerequisite for any horizontally-scaled architecture — without it, scaling adds capacity but not reliability.

  RECOMMENDED FIX
  Add a load balancer at every tier boundary. For Kubernetes: use an Ingress controller (nginx-ingress, Traefik) or a service mesh (Istio, Linkerd) for internal load balancing. For cloud: AWS ALB/NLB, GCP Load Balancer, or Azure Application Gateway. Configure health checks so failed pods are removed from rotation automatically. Use Layer 7 load balancing for HTTP — enables path-based routing and sticky sessions.

  CITATIONS
   → https://github.com/donnemartin/system-design-primer#load-balancer
   → https://github.com/ashishps1/awesome-system-design-resources
   → https://discord.com/blog/how-discord-stores-trillions-of-messages
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
   → https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116
----------------------------------------------------------------------

──────────────────────────────────────────────────────────────────────
  📊 OBSERVABILITY GAPS
──────────────────────────────────────────────────────────────────────

  ⚠️  [WARNING] No Observability Stack Mentioned — Flying Blind in Production

  PROBLEM
  Distributed systems without metrics, tracing, and structured logging are impossible to debug in production. When an incident occurs, engineers spend 80% of their time finding the problem and 20% fixing it. With proper observability, that ratio inverts. The average time to detect a production incident without monitoring is reported by users — not engineers.

  RECOMMENDED FIX
  Implement the three pillars of observability before going to production: 1. METRICS — Prometheus + Grafana (latency p50/p95/p99, error rate, throughput). 2. TRACING — OpenTelemetry + Jaeger/Tempo (distributed request tracing). 3. LOGGING — Structured JSON logs → ELK/Loki (searchable, correlated by trace ID). Set alerts on error rate > 1% and latency p99 > SLA threshold. Without these, you will learn about incidents from users, not dashboards.

  CITATIONS
   → https://netflixtechblog.com/tagged/observability
   → https://opentelemetry.io/docs/concepts/observability-primer/
   → https://discord.com/blog/how-discord-stores-trillions-of-messages
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
----------------------------------------------------------------------

  ⚠️  [WARNING] No On-Call Runbooks — Team Will Learn Incident Response Under Fire

  PROBLEM
  Systems going to production without documented on-call runbooks force engineers to debug and improvise during live incidents under maximum pressure. Netflix's Chaos Engineering programme was built specifically because they discovered their teams did not know how to respond to failures until those failures happened in production. For new teams at high scale, the first production incident without runbooks typically takes 3–5x longer to resolve than it should — and the extended downtime compounds the event backlog problem dramatically.

  ENGINEERING SCARS (from production post-mortems)
   • Eliminated Kafka broker management overhead for a sub-10-engineer team
   • Reduced end-to-end message delivery latency below 50ms p99
   • Prevented cascading failure propagation across 600+ microservices
   • Fallback responses kept user experience degraded-but-functional during partial outages

  RECOMMENDED FIX
  Before going to production, write runbooks for every known failure mode: 1. FAILURE SCENARIOS — broker down, consumer group rebalance, DLQ overflow, database connection pool exhaustion, downstream timeout cascade. 2. RUNBOOK STRUCTURE — detection signal (which alert fires), immediate mitigation (what to do in first 5 minutes), root cause investigation steps, escalation path. 3. GAME DAYS — run a scheduled failure drill before launch. Kill a broker in staging. Watch the team respond. Fix the gaps. Netflix's Chaos Monkey exists because they learned this lesson expensively. 4. ON-CALL ROTATION — defined before launch, not after first incident.

  CITATIONS
   → https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116
   → https://github.com/donnemartin/system-design-primer#availability-vs-consistency
   → https://github.com/ashishps1/awesome-system-design-resources
   → https://discord.com/blog/how-discord-stores-trillions-of-messages
   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
   → https://tesla.com/blog/engineering-telemetry
----------------------------------------------------------------------

======================================================================
  ArchGraph AI — Recommended Best Design
======================================================================
  Best Design for Architecture — 15 Engineers

  Based on your stack and 6 issue(s) detected, this is the recommended target architecture. Each layer addresses a specific failure mode documented in production post-mortems from companies at your scale.

──────────────────────────────────────────────────────────────────────
  🏗  ARCHITECTURE LAYERS
──────────────────────────────────────────────────────────────────────

  ┌─ API / Gateway Layer
  │  Component : nginx/ALB load balancer → API Gateway (rate limiting, auth, TLS) → Services [⚠️ add load balancer]
  │  Why       : Single entry point for auth, rate limiting, TLS termination, and routing
  │  Pattern   : Netflix API Resilience Pattern
  │
  ┌─ Service Layer
  │  Component : Microservices on Kubernetes [⚠️ add circuit breaker, ⚠️ add retry+timeout]
  │  Why       : Circuit breakers prevent cascading failure; retry+timeout bound tail latency
  │  Pattern   : Netflix Hystrix Pattern (600+ microservices)
  │
  ┌─ Observability Layer
  │  Component : Prometheus + Grafana + OpenTelemetry + structured logging (Loki) [⚠️ add Prometheus+Grafana+OpenTelemetry, ⚠️ write on-call runbooks]
  │  Why       : Without metrics+tracing+logging, engineers learn about incidents from users not dashboards
  │  Pattern   : Netflix Simian Army + OpenTelemetry standard
  │

──────────────────────────────────────────────────────────────────────
  ✅ IMPLEMENTATION CHECKLIST
──────────────────────────────────────────────────────────────────────

  01. Add load balancer (nginx Ingress on K8s, or AWS ALB) with health checks
  02. Add circuit breakers on all synchronous service calls (open after 5 failures/10s)
  03. Set explicit timeout on every outbound call (p99 latency × 3). Exponential backoff with jitter, max 3 retries.
  04. Set up Prometheus (metrics), Grafana (dashboards), OpenTelemetry (tracing), Loki (logs). Alert on error rate >1% and p99 > SLA.
  05. Write runbooks for every known failure mode before go-live. Define on-call rotation. Run a game day in staging.

──────────────────────────────────────────────────────────────────────
  🚫 WHAT NOT TO DO (from post-mortems)
──────────────────────────────────────────────────────────────────────

   ✗ Single API instance with no load balancer — one crash = full downtime
   ✗ Microservices without circuit breakers — one slow service takes down the entire call chain
   ✗ No timeout on downstream calls — hanging connections accumulate during partial failures
   ✗ No observability — engineers spend 80% of incident time finding the problem instead of fixing it
   ✗ No runbooks — team learns incident response under maximum pressure during a live production failure

──────────────────────────────────────────────────────────────────────
  📚 CITATIONS
──────────────────────────────────────────────────────────────────────

   → https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d
   → https://opentelemetry.io/docs/concepts/observability-primer/
   → https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116
======================================================================
```

---

## Finance - Failure Scenario
### Input
`payment processing, no idempotency keys, 2 engineers`

### Output
```text
======================================================================
  ArchGraph AI — Architecture Critique Report
======================================================================
  Architecture : payment processing, no idempotency keys, 2 engineers
  Team Size    : 2 engineers
  Domain       : Finance
  Overall Risk : CRITICAL
  Issues found : 1 (0 operational / 1 design / 0 security / 0 observability)
======================================================================

──────────────────────────────────────────────────────────────────────
  🏗  DESIGN ISSUES
──────────────────────────────────────────────────────────────────────

  ❌ [CRITICAL] CAP Theorem Violation — Eventual Consistency on Financial / Inventory Data
  Scale Match Score: 0.67/1.0

  PROBLEM
  Eventual consistency databases (Cassandra, DynamoDB in default mode, MongoDB with read preference secondary) on financial or inventory data create silent correctness bugs: double-charges, negative inventory, split-brain balances. The CAP theorem defines this tradeoff clearly — AP systems sacrifice consistency during network partitions. For financial data, a partition causing inconsistency is a compliance incident, not just a bug. The system-design-primer documents this as the #1 CAP theorem mistake.

  ENGINEERING SCARS (from production post-mortems)
   • Non-financial CRUD APIs where duplicate writes are acceptable
   • Systems without a persistent idempotency key store (e.g., pure in-memory cache)
   • Choosing AP (eventual consistency) for financial ledgers, payment records, or inventory counts
   • Choosing CP (strong consistency) for shopping carts or social feeds where availability matters more

  RECOMMENDED FIX
  Use a CP database (PostgreSQL, MySQL, CockroachDB, Spanner) with ACID guarantees for all financial, inventory, and ledger data. If using DynamoDB: enable strongly consistent reads and use transactions for balance/inventory mutations. If using Cassandra: use lightweight transactions (LWT) with SERIAL consistency — but be aware of the performance cost. Stripe's pattern: all financial writes go through a single Postgres primary with idempotency keys — never eventually consistent.

  CITATIONS
   → https://github.com/donnemartin/system-design-primer#cap-theorem
   → https://stripe.com/blog/idempotency
   → https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies
----------------------------------------------------------------------

======================================================================
  ArchGraph AI — Recommended Best Design
======================================================================
  Best Design for Finance Architecture — 2 Engineers

  Based on your stack and 1 issue(s) detected, this is the recommended target architecture. Each layer addresses a specific failure mode documented in production post-mortems from companies at your scale.

──────────────────────────────────────────────────────────────────────
  🏗  ARCHITECTURE LAYERS
──────────────────────────────────────────────────────────────────────

  ┌─ Observability Layer
  │  Component : Prometheus + Grafana + OpenTelemetry + structured logging (Loki) ✅
  │  Why       : Without metrics+tracing+logging, engineers learn about incidents from users not dashboards
  │  Pattern   : Netflix Simian Army + OpenTelemetry standard
  │

======================================================================
```

---

## Finance - Success Scenario
### Input
`immutable ledger system, 5 engineers`

### Output
```text
======================================================================
  ArchGraph AI — Architecture Critique Report
======================================================================
  Architecture : immutable ledger system, 5 engineers
  Team Size    : 5 engineers
  Domain       : General
  Overall Risk : CRITICAL
  Issues found : 1 (0 operational / 1 design / 0 security / 0 observability)
======================================================================

──────────────────────────────────────────────────────────────────────
  🏗  DESIGN ISSUES
──────────────────────────────────────────────────────────────────────

  ❌ [CRITICAL] CAP Theorem Violation — Eventual Consistency on Financial / Inventory Data

  PROBLEM
  Eventual consistency databases (Cassandra, DynamoDB in default mode, MongoDB with read preference secondary) on financial or inventory data create silent correctness bugs: double-charges, negative inventory, split-brain balances. The CAP theorem defines this tradeoff clearly — AP systems sacrifice consistency during network partitions. For financial data, a partition causing inconsistency is a compliance incident, not just a bug. The system-design-primer documents this as the #1 CAP theorem mistake.

  ENGINEERING SCARS (from production post-mortems)
   • Teams under 3 infrastructure engineers (operational overhead too high)
   • Workloads with predominantly write-heavy access patterns without read SLA requirements
   • Non-financial CRUD APIs where duplicate writes are acceptable
   • Systems without a persistent idempotency key store (e.g., pure in-memory cache)

  RECOMMENDED FIX
  Use a CP database (PostgreSQL, MySQL, CockroachDB, Spanner) with ACID guarantees for all financial, inventory, and ledger data. If using DynamoDB: enable strongly consistent reads and use transactions for balance/inventory mutations. If using Cassandra: use lightweight transactions (LWT) with SERIAL consistency — but be aware of the performance cost. Stripe's pattern: all financial writes go through a single Postgres primary with idempotency keys — never eventually consistent.

  CITATIONS
   → https://github.com/donnemartin/system-design-primer#cap-theorem
   → https://stripe.com/blog/idempotency
   → https://discord.com/blog/how-discord-stores-trillions-of-messages
   → https://innovation.philips.com/blog/iomt-edge-architecture
----------------------------------------------------------------------

======================================================================
  ArchGraph AI — Recommended Best Design
======================================================================
  Best Design for Architecture — 5 Engineers

  Based on your stack and 1 issue(s) detected, this is the recommended target architecture. Each layer addresses a specific failure mode documented in production post-mortems from companies at your scale.

──────────────────────────────────────────────────────────────────────
  🏗  ARCHITECTURE LAYERS
──────────────────────────────────────────────────────────────────────

  ┌─ Observability Layer
  │  Component : Prometheus + Grafana + OpenTelemetry + structured logging (Loki) ✅
  │  Why       : Without metrics+tracing+logging, engineers learn about incidents from users not dashboards
  │  Pattern   : Netflix Simian Army + OpenTelemetry standard
  │

======================================================================
```

---

## AI Infrastructure - Failure Scenario
### Input
`training LLM, no KV-cache recycling, 5 engineers, H100 cluster`

### Output
```text
======================================================================
  ArchGraph AI — Architecture Critique Report
======================================================================
  Architecture : training LLM, no KV-cache recycling, 5 engineers, H100 cluster
  Team Size    : 5 engineers
  Domain       : AIInfra
  Overall Risk : CRITICAL
  Issues found : 2 (0 operational / 2 design / 0 security / 0 observability)
======================================================================

──────────────────────────────────────────────────────────────────────
  🏗  DESIGN ISSUES
──────────────────────────────────────────────────────────────────────

  ⚠️  [WARNING] Sequential LLM Agent Chain — KV-Cache Stall and Latency Risk

  PROBLEM
  Deep sequential agent chains cause compounding context growth. Each hop forces the LLM to re-process the accumulated context, causing KV-cache evictions and exponential latency growth under load. A 4-step sequential chain at 1,000 docs/hour will typically exceed a 3-second latency SLA.

  ENGINEERING SCARS (from production post-mortems)
   • Parallel branches increase peak memory pressure proportionally
   • Branch merge logic adds engineering complexity — incorrect merges cause context corruption
   • Feature store adds infrastructure cost and operational complexity
   • Point-in-time correct joins significantly increase training data pipeline complexity

  RECOMMENDED FIX
  Shift to a Parallel Router-Classifier Architecture (Anthropic Pattern). Run independent extraction/validation branches in parallel. Merge metadata in a single final step using PagedAttention to recycle KV-cache entries across branches.

  CITATIONS
   → https://anthropic.com/research/building-effective-agents
   → https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies
----------------------------------------------------------------------

  ❌ [CRITICAL] No Feature Store — Training-Serving Skew Risk

  PROBLEM
  Without a centralised feature store, features are computed differently at training time (batch, from historical data) vs serving time (real-time, from live data). This training-serving skew causes silent model accuracy degradation in production that is invisible in offline metrics. Airbnb, DoorDash, and Uber all documented this as their #1 ML infrastructure failure mode. A model can pass all offline tests and fail silently in production for weeks before anyone notices the accuracy has collapsed.

  ENGINEERING SCARS (from production post-mortems)
   • Eliminates silent model accuracy degradation caused by feature computation differences
   • Airbnb reported 15% prediction quality improvement after unifying feature pipelines
   • Feature store adds infrastructure cost and operational complexity
   • Point-in-time correct joins significantly increase training data pipeline complexity

  RECOMMENDED FIX
  Implement a feature store (Feast, Tecton, Hopsworks, or custom Redis-backed) that serves identical features at training and inference time. Key requirements: 1. Point-in-time correct joins for training — never use future data. 2. Online store (Redis/DynamoDB) for low-latency serving. 3. Offline store (S3/BigQuery) for training data retrieval. 4. Automated skew detection — alert when online/offline distributions diverge >5%. Airbnb reported 15% prediction quality improvement after unifying feature pipelines.

  CITATIONS
   → https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies
   → https://www.uber.com/blog/michelangelo-machine-learning-platform/
   → https://docs.feast.dev/
----------------------------------------------------------------------

======================================================================
  ArchGraph AI — Recommended Best Design
======================================================================
  Best Design for AIInfra Architecture — 5 Engineers

  Based on your stack and 2 issue(s) detected, this is the recommended target architecture. Each layer addresses a specific failure mode documented in production post-mortems from companies at your scale.

──────────────────────────────────────────────────────────────────────
  🏗  ARCHITECTURE LAYERS
──────────────────────────────────────────────────────────────────────

  ┌─ ML Infrastructure Layer
  │  Component : Feature Store (Feast) + Model Registry (MLflow) + Shadow Deployment [⚠️ add feature store]
  │  Why       : Feature store prevents training-serving skew; shadow deploy catches regressions before users see them
  │  Pattern   : Uber Michelangelo + Netflix Model Deployment Patterns
  │
  ┌─ Observability Layer
  │  Component : Prometheus + Grafana + OpenTelemetry + structured logging (Loki) ✅
  │  Why       : Without metrics+tracing+logging, engineers learn about incidents from users not dashboards
  │  Pattern   : Netflix Simian Army + OpenTelemetry standard
  │

──────────────────────────────────────────────────────────────────────
  ✅ IMPLEMENTATION CHECKLIST
──────────────────────────────────────────────────────────────────────

  01. Implement feature store (Feast/Tecton): unified online (Redis) + offline (S3) feature access

──────────────────────────────────────────────────────────────────────
  🚫 WHAT NOT TO DO (from post-mortems)
──────────────────────────────────────────────────────────────────────

   ✗ Features computed differently at training vs serving — silent model accuracy collapse in production (Airbnb, DoorDash, Uber all documented this)

──────────────────────────────────────────────────────────────────────
  📚 CITATIONS
──────────────────────────────────────────────────────────────────────

   → https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies
======================================================================
```

---

## AI Infrastructure - Success Scenario
### Input
`Anthropic pattern, parallel router-classifier, 20 engineers`

### Output
```text
======================================================================
  ArchGraph AI — Architecture Critique Report
======================================================================
  Architecture : Anthropic pattern, parallel router-classifier, 20 engineers
  Team Size    : 20 engineers
  Domain       : General
  Overall Risk : OK
  Issues found : 0 (0 operational / 0 design / 0 security / 0 observability)
======================================================================

  ✅  No critical issues detected.


======================================================================
  ArchGraph AI — Recommended Best Design
======================================================================
  Best Design for Architecture — 20 Engineers

  Your architecture has no critical issues. This blueprint confirms the patterns you already have and highlights what to preserve as you scale.

──────────────────────────────────────────────────────────────────────
  🏗  ARCHITECTURE LAYERS
──────────────────────────────────────────────────────────────────────

  ┌─ Observability Layer
  │  Component : Prometheus + Grafana + OpenTelemetry + structured logging (Loki) ✅
  │  Why       : Without metrics+tracing+logging, engineers learn about incidents from users not dashboards
  │  Pattern   : Netflix Simian Army + OpenTelemetry standard
  │

======================================================================
```

---

## MedTech - Failure Scenario
### Input
`offline-first hospital monitors, no local alarm safety buffer, 2 engineers`

### Output
```text
======================================================================
  ArchGraph AI — Architecture Critique Report
======================================================================
  Architecture : offline-first hospital monitors, no local alarm safety buffer, 2 engineers
  Team Size    : 2 engineers
  Domain       : General
  Overall Risk : OK
  Issues found : 0 (0 operational / 0 design / 0 security / 0 observability)
======================================================================

  ✅  No critical issues detected.


======================================================================
  ArchGraph AI — Recommended Best Design
======================================================================
  Best Design for Architecture — 2 Engineers

  Your architecture has no critical issues. This blueprint confirms the patterns you already have and highlights what to preserve as you scale.

──────────────────────────────────────────────────────────────────────
  🏗  ARCHITECTURE LAYERS
──────────────────────────────────────────────────────────────────────

  ┌─ Observability Layer
  │  Component : Prometheus + Grafana + OpenTelemetry + structured logging (Loki) ✅
  │  Why       : Without metrics+tracing+logging, engineers learn about incidents from users not dashboards
  │  Pattern   : Netflix Simian Army + OpenTelemetry standard
  │

======================================================================
```

---

## MedTech - Success Scenario
### Input
`GE Hub-and-Spoke Edge architecture, 10 engineers`

### Output
```text
======================================================================
  ArchGraph AI — Architecture Critique Report
======================================================================
  Architecture : GE Hub-and-Spoke Edge architecture, 10 engineers
  Team Size    : 10 engineers
  Domain       : General
  Overall Risk : OK
  Issues found : 0 (0 operational / 0 design / 0 security / 0 observability)
======================================================================

  ✅  No critical issues detected.


======================================================================
  ArchGraph AI — Recommended Best Design
======================================================================
  Best Design for Architecture — 10 Engineers

  Your architecture has no critical issues. This blueprint confirms the patterns you already have and highlights what to preserve as you scale.

──────────────────────────────────────────────────────────────────────
  🏗  ARCHITECTURE LAYERS
──────────────────────────────────────────────────────────────────────

  ┌─ Observability Layer
  │  Component : Prometheus + Grafana + OpenTelemetry + structured logging (Loki) ✅
  │  Why       : Without metrics+tracing+logging, engineers learn about incidents from users not dashboards
  │  Pattern   : Netflix Simian Army + OpenTelemetry standard
  │

======================================================================
```

---

## Edge / IoT - Failure Scenario
### Input
`1M fleet telemetry devices, direct writes to Postgres, 4 engineers`

### Output
```text
======================================================================
  ArchGraph AI — Architecture Critique Report
======================================================================
  Architecture : 1M fleet telemetry devices, direct writes to Postgres, 4 engineers
  Team Size    : 4 engineers
  Domain       : General
  Overall Risk : CRITICAL
  Issues found : 2 (0 operational / 2 design / 0 security / 0 observability)
======================================================================

──────────────────────────────────────────────────────────────────────
  🏗  DESIGN ISSUES
──────────────────────────────────────────────────────────────────────

  ❌ [CRITICAL] Single Database Instance — No Failover
  Scale Match Score: 0.27/1.0 ← TEAM TOO SMALL

  PROBLEM
  A single database instance with no replica or standby is a hard single point of failure. Instance failure, disk corruption, or a botched migration causes complete service downtime with no automatic recovery path. Recovery from a snapshot typically takes 15–60 minutes minimum, during which the service is completely unavailable.

  RECOMMENDED FIX
  Add a read replica as a minimum for failover capability (promotes to primary in ~30s). For production: use managed multi-AZ (AWS RDS Multi-AZ, Aurora, GCP Cloud SQL HA). Implement automated failover — manual promotion takes too long under incident stress. Test failover quarterly; most teams discover it does not work during an actual incident.

  CITATIONS
   → https://aws.amazon.com/rds/features/multi-az/
   → https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116
   → https://github.com/donnemartin/system-design-primer#master-slave-replication
----------------------------------------------------------------------

  ⚠️  [WARNING] No Caching Layer — Database Will Become the Bottleneck

  PROBLEM
  Systems that hit the database on every request hit a hard scalability wall at moderate traffic levels. Read-heavy workloads (>70% reads) degrade database performance for writes, increasing latency across the board. Adding database capacity is expensive and has diminishing returns. Most application data has high read-to-write ratios and is cacheable.

  RECOMMENDED FIX
  Add Redis or Memcached as a read-through cache in front of the database. Cache aggressively for data with TTL > 1 second (user profiles, product catalog, configuration, session data). Use cache-aside pattern: read from cache, on miss read from DB and populate cache. For APIs: add CDN caching for public responses (CloudFront, Fastly). Target: 80%+ cache hit rate before scaling the database.

  CITATIONS
   → https://engineering.fb.com/2013/06/25/core-infra/tao-the-power-of-the-graph/
   → https://discord.com/blog/how-discord-stores-trillions-of-messages
   → https://stripe.com/blog/idempotency
   → https://github.com/donnemartin/system-design-primer#content-delivery-network
----------------------------------------------------------------------

======================================================================
  ArchGraph AI — Recommended Best Design
======================================================================
  Best Design for Architecture — 4 Engineers

  Based on your stack and 2 issue(s) detected, this is the recommended target architecture. Each layer addresses a specific failure mode documented in production post-mortems from companies at your scale.

──────────────────────────────────────────────────────────────────────
  🏗  ARCHITECTURE LAYERS
──────────────────────────────────────────────────────────────────────

  ┌─ Data Layer
  │  Component : PostgreSQL (multi-AZ primary + read replica) + Redis cache [⚠️ add read replica / failover, ⚠️ add Redis cache]
  │  Why       : Multi-AZ gives <30s failover; Redis cache targets 80%+ hit rate before DB scales
  │  Pattern   : system-design-primer read replica + Discord ScyllaDB patterns
  │
  ┌─ Observability Layer
  │  Component : Prometheus + Grafana + OpenTelemetry + structured logging (Loki) ✅
  │  Why       : Without metrics+tracing+logging, engineers learn about incidents from users not dashboards
  │  Pattern   : Netflix Simian Army + OpenTelemetry standard
  │

──────────────────────────────────────────────────────────────────────
  ✅ IMPLEMENTATION CHECKLIST
──────────────────────────────────────────────────────────────────────

  01. Add read replica with automated failover (RDS Multi-AZ, Aurora, or Cloud SQL HA)
  02. Add Redis cache (cache-aside pattern). Target 80%+ hit rate. TTL ≥ 1s for stable reads.

──────────────────────────────────────────────────────────────────────
  🚫 WHAT NOT TO DO (from post-mortems)
──────────────────────────────────────────────────────────────────────

   ✗ Single database instance — disk failure or bad migration = 15–60 min downtime with no automatic recovery
   ✗ All reads hitting database directly — hits hard scalability wall at moderate traffic

======================================================================
```

---

## Edge / IoT - Success Scenario
### Input
`Tesla Edge pre-aggregation, fleet telemetry batching, 12 engineers`

### Output
```text
======================================================================
  ArchGraph AI — Architecture Critique Report
======================================================================
  Architecture : Tesla Edge pre-aggregation, fleet telemetry batching, 12 engineers
  Team Size    : 12 engineers
  Domain       : General
  Overall Risk : OK
  Issues found : 0 (0 operational / 0 design / 0 security / 0 observability)
======================================================================

  ✅  No critical issues detected.


======================================================================
  ArchGraph AI — Recommended Best Design
======================================================================
  Best Design for Architecture — 12 Engineers

  Your architecture has no critical issues. This blueprint confirms the patterns you already have and highlights what to preserve as you scale.

──────────────────────────────────────────────────────────────────────
  🏗  ARCHITECTURE LAYERS
──────────────────────────────────────────────────────────────────────

  ┌─ Observability Layer
  │  Component : Prometheus + Grafana + OpenTelemetry + structured logging (Loki) ✅
  │  Why       : Without metrics+tracing+logging, engineers learn about incidents from users not dashboards
  │  Pattern   : Netflix Simian Army + OpenTelemetry standard
  │

======================================================================
```

---



# Appended Test Results
# ArchGraph AI — Test Results
# Date: 2026-06-29  |  Python: 3.12  |  Platform: Linux (fully offline)
# Run: python tests/test_archgraph.py -v
# ══════════════════════════════════════════════════════════════════════

Ran 98 tests in 0.091s — ALL PASS ✅

SUITE BREAKDOWN:
  Suite 1  — Ingestion                                               3 tests  ✅
  Suite 2  — InMemoryGraph (17 seed techniques)                      6 tests  ✅
  Suite 3  — ArchitectureInput Parser                                6 tests  ✅
  Suite 4  — Operational Rules                                       6 tests  ✅
  Suite 5  — Design Issues (13 rules)                                26 tests  ✅
  Suite 6  — Team Maturity Rules                                     5 tests  ✅
  Suite 7  — ML Infrastructure Rules                                10 tests  ✅
  Suite 8  — Security Issues                                         4 tests  ✅
  Suite 9  — Observability Gaps                                      2 tests  ✅
  Suite 10 — Category Tagging                                        6 tests  ✅
  Suite 11 — Fully Addressed Architecture → OK                       2 tests  ✅
  Suite 12 — Design Blueprint (NEW)                                  18 tests  ✅
  Suite 13 — Render Output                                           6 tests  ✅

══════════════════════════════════════════════════════════════════════

The tool now generates a recommended target architecture alongside every
critique — not just what's wrong, but what GOOD looks like for your
specific stack.

EXAMPLE OUTPUT for "microservice REST API postgres kafka 5 engineers
public web frontend react":

  🏗  ARCHITECTURE LAYERS
  ┌─ Client / CDN Layer
  │  Component : React/Vue SPA → ⚠️ ADD CDN (CloudFront/Cloudflare)
  │  Why       : CDN reduces origin load 80–90%, cuts global latency <50ms
  │  Pattern   : system-design-primer (donnemartin)
  │
  ┌─ API / Gateway Layer
  │  Component : nginx/ALB → API Gateway [⚠️ add LB, ⚠️ add rate limit, ⚠️ add auth]
  │  Pattern   : Netflix API Resilience Pattern
  │
  ┌─ Service Layer
  │  Component : Microservices on K8s [⚠️ add circuit breaker, ⚠️ add retry]
  │  Pattern   : Netflix Hystrix Pattern (600+ microservices)
  │
  ┌─ Data Layer
  │  Component : PostgreSQL multi-AZ + Redis [⚠️ add replica, ⚠️ add cache]
  │  Pattern   : system-design-primer + Discord ScyllaDB patterns

  ✅ IMPLEMENTATION CHECKLIST
  01. Add CDN for all static assets
  02. Add load balancer with health checks
  03. Implement rate limiting at gateway
  ... (one numbered action per gap found)

  🚫 WHAT NOT TO DO (from post-mortems)
   ✗ Single API instance — one crash = full downtime
   ✗ No auth — #1 cause of API data breaches (OWASP)
   ... (anti-pattern per gap, grounded in real incidents)

WHEN ARCHITECTURE IS ALREADY GOOD:
  Layers marked with ✅ instead of ⚠️ — confirms what to KEEP, not just
  what to fix. Checklist and anti-patterns sections shrink to only the
  real remaining gaps.

BLUEPRINT LAYERS GENERATED CONDITIONALLY:
  Client/CDN Layer        — when frontend/static assets detected
  API/Gateway Layer        — when REST/GraphQL/gRPC/microservice detected
  Service Layer            — when microservice/kubernetes detected
  Messaging/Event Layer    — when kafka/queue/event-driven detected
  Data Layer                — when database mentioned
  ML Infrastructure Layer   — when ml/model/inference mentioned
  Observability Layer       — always included
  Edge Safety Layer         — MedTech domain only (FDA/patient safety)

══════════════════════════════════════════════════════════════════════
COMPLETE RULE INVENTORY (24 rules, 4 categories) — unchanged from v3:

  🔧 OPERATIONAL (6)  🏗 DESIGN (13)  🔒 SECURITY (2)  📊 OBSERVABILITY (2)
  ML Infrastructure rules included within OPERATIONAL/DESIGN above.

KNOWLEDGE GRAPH — 17 seed techniques from:
  Production post-mortems (Discord, Netflix, Stripe, Anthropic, Philips, Tesla)
  system-design-primer (donnemartin, 355k ⭐)
  ML System Design Case Studies (Engineer1999, 9.8k ⭐)
══════════════════════════════════════════════════════════════════════
