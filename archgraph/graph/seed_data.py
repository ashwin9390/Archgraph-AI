"""
ArchGraph AI — Pre-loaded seed techniques.
These are manually curated extractions from public engineering blogs.
Used to bootstrap the graph so users get a working demo immediately.
"""

from __future__ import annotations

SEED_TECHNIQUES: list[dict] = [
    # ── Discord ──────────────────────────────────────────────────────────────
    {
        "technique_id": "discord_scylladb_migration",
        "name": "ScyllaDB Migration from Cassandra for Hot-Storage",
        "origin_company": "Discord",
        "source_url": "https://discord.com/blog/how-discord-stores-trillions-of-messages",
        "domain_tags": ["RealTime", "HighThroughput", "Infrastructure"],
        "design_techniques": ["Wide-column hot storage", "ScyllaDB shared-nothing architecture", "Cassandra-to-ScyllaDB live migration"],
        "positive_outcomes": [
            "p99 read latency dropped from 40ms to 15ms",
            "Reduced node count from 177 Cassandra nodes to 72 ScyllaDB nodes",
            "Eliminated GC pressure that caused Cassandra tail latency spikes",
        ],
        "negative_side_effects": [
            "Migration required dual-write period with operational complexity",
            "Team needed to learn ScyllaDB tuning parameters from scratch",
        ],
        "counter_indicators": [
            "Teams under 3 infrastructure engineers (operational overhead too high)",
            "Workloads with predominantly write-heavy access patterns without read SLA requirements",
        ],
        "scale_context": {
            "messages_stored": "Trillions",
            "team_size_min": 3,
        },
    },
    {
        "technique_id": "discord_kafka_elimination",
        "name": "Kafka Elimination via Persistent WebSocket Connections",
        "origin_company": "Discord",
        "source_url": "https://discord.com/blog/how-discord-stores-trillions-of-messages",
        "domain_tags": ["RealTime", "HighThroughput", "Infrastructure"],
        "design_techniques": ["Persistent WebSocket fanout", "Gateway node sharding", "Session-state co-location"],
        "positive_outcomes": [
            "Eliminated Kafka broker management overhead for a sub-10-engineer team",
            "Reduced end-to-end message delivery latency below 50ms p99",
        ],
        "negative_side_effects": [
            "Harder to replay events post-hoc vs. Kafka's durable log",
            "Gateway nodes become single points of failure without careful session pinning",
        ],
        "counter_indicators": [
            "Systems needing event replay or audit log of all messages",
            "Architectures with stateless consumers that scale independently",
        ],
        "scale_context": {
            "concurrent_users": "Millions",
            "team_size_min": 2,
        },
    },

    # ── Netflix ──────────────────────────────────────────────────────────────
    {
        "technique_id": "netflix_circuit_breaker_hystrix",
        "name": "Circuit Breaker Pattern (Hystrix) for Microservice Fault Isolation",
        "origin_company": "Netflix",
        "source_url": "https://netflixtechblog.com/making-the-netflix-api-more-resilient-a8ec62159c2d",
        "domain_tags": ["WebScale", "Microservices", "HighAvailability"],
        "design_techniques": ["Circuit Breaker", "Bulkhead isolation", "Fallback response chains"],
        "positive_outcomes": [
            "Prevented cascading failure propagation across 600+ microservices",
            "Fallback responses kept user experience degraded-but-functional during partial outages",
        ],
        "negative_side_effects": [
            "Hystrix thread pools added 10–15ms latency overhead per service hop",
            "Fallback logic must be explicitly maintained — silent staleness risk",
        ],
        "counter_indicators": [
            "Monolithic architectures where inter-process calls are in-process",
            "Systems with fewer than 5 downstream dependencies (overhead not justified)",
        ],
        "scale_context": {
            "microservices_count": 600,
            "team_size_min": 10,
        },
    },
    {
        "technique_id": "netflix_chaos_monkey",
        "name": "Chaos Engineering via Chaos Monkey for Resilience Validation",
        "origin_company": "Netflix",
        "source_url": "https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116",
        "domain_tags": ["WebScale", "HighAvailability", "Infrastructure"],
        "design_techniques": ["Chaos Monkey random instance termination", "Simian Army suite", "Game Day drills"],
        "positive_outcomes": [
            "Identified hidden single-points-of-failure before production incidents",
            "Forced engineering culture of designing for failure from day one",
        ],
        "negative_side_effects": [
            "Requires mature on-call rotation and incident response before enabling",
            "False positives cause alert fatigue if blast radius is not bounded",
        ],
        "counter_indicators": [
            "Teams without a working on-call rotation or incident runbooks",
            "Early-stage products without redundancy built into the data layer",
        ],
        "scale_context": {
            "team_size_min": 15,
        },
    },

    # ── Stripe ────────────────────────────────────────────────────────────────
    {
        "technique_id": "stripe_idempotency_keys",
        "name": "Idempotency Keys for Distributed Payment Safety",
        "origin_company": "Stripe",
        "source_url": "https://stripe.com/blog/idempotency",
        "domain_tags": ["Finance", "Payments", "Compliance"],
        "design_techniques": ["Client-generated idempotency keys", "Server-side deduplication store", "At-most-once payment execution"],
        "positive_outcomes": [
            "Eliminated duplicate charge risk during network retries",
            "Enabled safe client-side retry logic without coordination overhead",
        ],
        "negative_side_effects": [
            "Idempotency store adds a synchronous read per payment request",
            "Keys must be scoped correctly — wrong scoping causes silent de-duplication of distinct payments",
        ],
        "counter_indicators": [
            "Non-financial CRUD APIs where duplicate writes are acceptable",
            "Systems without a persistent idempotency key store (e.g., pure in-memory cache)",
        ],
        "scale_context": {
            "team_size_min": 2,
        },
    },

    # ── Anthropic / OpenAI ────────────────────────────────────────────────────
    {
        "technique_id": "anthropic_parallel_router_classifier",
        "name": "Parallel Router-Classifier Architecture for Multi-Agent Pipelines",
        "origin_company": "Anthropic",
        "source_url": "https://anthropic.com/research/building-effective-agents",
        "domain_tags": ["AIInfra", "MLOps"],
        "design_techniques": [
            "Parallel sub-agent execution",
            "Router-Classifier pattern",
            "KV-cache recycling via PagedAttention",
            "Context window budgeting per branch",
        ],
        "positive_outcomes": [
            "Reduced end-to-end agent pipeline latency by 60% vs. sequential chain",
            "KV-cache recycling eliminated redundant prefill computation across branches",
        ],
        "negative_side_effects": [
            "Parallel branches increase peak memory pressure proportionally",
            "Branch merge logic adds engineering complexity — incorrect merges cause context corruption",
        ],
        "counter_indicators": [
            "Sequential tasks with strict data dependencies between steps",
            "Systems without GPU VRAM headroom for parallel KV-cache allocation",
        ],
        "scale_context": {
            "docs_per_hour_tested": 1000,
            "target_latency_seconds": 3,
            "team_size_min": 3,
        },
    },

    # ── Philips HealthTech ────────────────────────────────────────────────────
    {
        "technique_id": "philips_iomt_edge_hub_spoke",
        "name": "Tiered Hub-and-Spoke Edge Architecture for Life-Critical IoMT",
        "origin_company": "Philips HealthTech",
        "source_url": "https://innovation.philips.com/blog/iomt-edge-architecture",
        "domain_tags": ["MedTech", "IoMT", "Compliance"],
        "design_techniques": [
            "Air-gapped bedside edge appliance",
            "Hardwired fail-safe relay alarms",
            "Offline-first sync engine",
            "Encrypted compressed telemetry batch upload",
        ],
        "positive_outcomes": [
            "Patient alarms fire locally even during total WAN/LAN outage",
            "HIPAA audit trail maintained via append-only local ledger with cloud sync",
            "Regulatory compliance with FDA SaMD Class II/III guidelines",
        ],
        "negative_side_effects": [
            "Edge appliances require on-site firmware update lifecycle management",
            "Dual storage (edge + cloud) increases infrastructure cost by ~30%",
        ],
        "counter_indicators": [
            "Non-life-critical IoT (e.g., building sensors) where cloud dependency is acceptable",
            "Systems with guaranteed 99.999% WAN uptime contracts and independent alerting hardware",
        ],
        "scale_context": {
            "patient_uptime_requirement": "99.9999%",
            "network_failure_tolerance": "Full LAN/WAN outage",
            "team_size_min": 5,
        },
    },

    # ── system-design-primer (donnemartin) ───────────────────────────────────
    {
        "technique_id": "sdp_cdn_static_offload",
        "name": "CDN for Static Asset and API Response Offload",
        "origin_company": "donnemartin/system-design-primer",
        "source_url": "https://github.com/donnemartin/system-design-primer#content-delivery-network",
        "domain_tags": ["WebScale", "EdgeComputing"],
        "design_techniques": [
            "Edge-cached static assets",
            "CDN pull vs push strategy",
            "Cache-Control header tuning",
        ],
        "positive_outcomes": [
            "Reduces origin server load by 80–90% for read-heavy public content",
            "Cuts p99 latency for global users from 300ms to under 50ms",
            "Eliminates bandwidth cost for repeated static asset delivery",
        ],
        "negative_side_effects": [
            "CDN cache invalidation is slow — stale content can persist for minutes",
            "Dynamic personalised responses cannot be cached at CDN layer",
            "Additional cost and complexity for cache purge management",
        ],
        "counter_indicators": [
            "Fully dynamic, personalised APIs with no cacheable responses",
            "Internal-only services with no global user distribution",
            "Architectures where cache invalidation latency would violate data freshness SLA",
        ],
        "scale_context": {
            "team_size_min": 1,
        },
    },
    {
        "technique_id": "sdp_sql_read_replica",
        "name": "SQL Read Replica for Cache Miss Handling and Read Scaling",
        "origin_company": "donnemartin/system-design-primer",
        "source_url": "https://github.com/donnemartin/system-design-primer#master-slave-replication",
        "domain_tags": ["WebScale", "DataEngineering"],
        "design_techniques": [
            "Master-slave replication",
            "Read replica routing",
            "Cache-aside with replica fallback",
        ],
        "positive_outcomes": [
            "Handles cache misses without overloading the write primary",
            "Horizontal read scaling — add replicas as read load grows",
            "Provides a promotion path to standby primary on failure",
        ],
        "negative_side_effects": [
            "Replicas lag behind primary under heavy write load — stale reads possible",
            "Replication lag can cause read-your-writes consistency failures",
            "Promotion to primary requires application-level failover logic",
        ],
        "counter_indicators": [
            "Workloads requiring strong read-after-write consistency (banking, ledger)",
            "Write-heavy workloads where replica lag exceeds acceptable staleness window",
            "Single-region deployments where read load is not the bottleneck",
        ],
        "scale_context": {
            "team_size_min": 2,
        },
    },
    {
        "technique_id": "sdp_cap_theorem_ap_vs_cp",
        "name": "CAP Theorem — Consistency vs Availability Tradeoff in Distributed Systems",
        "origin_company": "donnemartin/system-design-primer",
        "source_url": "https://github.com/donnemartin/system-design-primer#cap-theorem",
        "domain_tags": ["WebScale", "DataEngineering", "Finance"],
        "design_techniques": [
            "CP (Consistency + Partition Tolerance) — blocks on partition",
            "AP (Availability + Partition Tolerance) — serves stale data on partition",
            "Eventual consistency with conflict resolution",
        ],
        "positive_outcomes": [
            "CP systems guarantee no split-brain data corruption (critical for payments)",
            "AP systems stay available during network partitions (critical for carts, feeds)",
            "Explicit CAP choice prevents silent data inconsistency bugs in production",
        ],
        "negative_side_effects": [
            "CP systems become unavailable during network partitions — user-visible downtime",
            "AP systems serve stale or conflicting data — requires merge/conflict resolution",
            "Wrong CAP choice is a structural design error that cannot be fixed without re-architecture",
        ],
        "counter_indicators": [
            "Choosing AP (eventual consistency) for financial ledgers, payment records, or inventory counts",
            "Choosing CP (strong consistency) for shopping carts or social feeds where availability matters more",
            "Not explicitly choosing — implicit eventual consistency in a payments system is a compliance risk",
        ],
        "scale_context": {
            "team_size_min": 2,
        },
    },

    # ── Tesla ────────────────────────────────────────────────────────────────
    {
        "technique_id": "tesla_edge_telemetry_batching",
        "name": "Edge-Side Telemetry Pre-Aggregation for Fleet IoT",
        "origin_company": "Tesla",
        "source_url": "https://tesla.com/blog/engineering-telemetry",
        "domain_tags": ["HardwareCoDesign", "EdgeIoT"],
        "design_techniques": [
            "Regional hub pre-aggregation",
            "Lossy compression at edge",
            "Serverless managed queue for cloud ingestion sink",
        ],
        "positive_outcomes": [
            "Reduced cloud ingestion bandwidth by 80% vs. direct-stream architecture",
            "Eliminated Kafka broker management overhead for fleet telemetry team",
            "Maintained data fidelity for safety-critical signals while compressing diagnostics",
        ],
        "negative_side_effects": [
            "Pre-aggregation at edge loses per-vehicle raw event granularity",
            "Regional hubs introduce an additional failure domain to manage",
        ],
        "counter_indicators": [
            "Workloads requiring raw per-event replay (e.g., regulatory audit of every CAN bus frame)",
            "Small fleets under 10,000 devices where direct streaming is operationally simpler",
        ],
        "scale_context": {
            "devices": "Millions of vehicles",
            "writes_per_second": 60000,
            "team_size_min": 2,
        },
    },

    # ── ML System Design Case Studies (Engineer1999) ──────────────────────────
    # Source: github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies
    # 300+ case studies from 80+ companies — we extract the infrastructure failure modes only.
    {
        "technique_id": "mlsd_training_serving_skew",
        "name": "Training-Serving Skew Detection and Feature Store Consistency",
        "origin_company": "Airbnb / DoorDash / Uber Michelangelo",
        "source_url": "https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
        "domain_tags": ["AIInfra", "MLOps", "DataEngineering"],
        "design_techniques": [
            "Centralised feature store (Feast, Tecton, Hopsworks)",
            "Feature versioning with point-in-time correct joins",
            "Online/offline feature parity validation",
            "Skew detection via KL divergence on feature distributions",
        ],
        "positive_outcomes": [
            "Eliminates silent model accuracy degradation caused by feature computation differences",
            "Airbnb reported 15% prediction quality improvement after unifying feature pipelines",
            "Uber Michelangelo reduced model debugging time by 60% with centralised feature store",
        ],
        "negative_side_effects": [
            "Feature store adds infrastructure cost and operational complexity",
            "Point-in-time correct joins significantly increase training data pipeline complexity",
            "Teams without MLOps maturity often skip validation until a silent accuracy collapse occurs",
        ],
        "counter_indicators": [
            "Simple batch scoring pipelines where training and inference use identical code paths",
            "Models with human-in-the-loop validation before predictions reach users",
            "Prototypes or internal tools where prediction accuracy is not business-critical",
        ],
        "scale_context": {
            "team_size_min": 2,
        },
    },
    {
        "technique_id": "mlsd_model_versioning_shadow_deploy",
        "name": "Model Versioning with Shadow Deployment and Automated Rollback",
        "origin_company": "Netflix / Airbnb / LinkedIn",
        "source_url": "https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
        "domain_tags": ["AIInfra", "MLOps"],
        "design_techniques": [
            "Shadow deployment — new model runs in parallel, predictions logged but not served",
            "Canary release — new model serves small traffic slice (1–5%) before full rollout",
            "Automated rollback on metric degradation (p99 latency spike or accuracy drop)",
            "Model registry with immutable versioned artifacts",
        ],
        "positive_outcomes": [
            "Netflix catches model regressions in shadow mode before they reach any user",
            "Automated rollback reduces mean time to recovery from hours to under 5 minutes",
            "Model registry enables reproducible re-deployment of any historical model version",
        ],
        "negative_side_effects": [
            "Shadow deployment doubles inference compute cost during rollout period",
            "Canary evaluation requires sufficient traffic volume for statistical significance",
            "Automated rollback triggers require carefully tuned thresholds to avoid false positives",
        ],
        "counter_indicators": [
            "Low-traffic internal tools where manual review before deployment is feasible",
            "Models where shadow predictions cannot be collected without user interaction",
        ],
        "scale_context": {
            "team_size_min": 3,
        },
    },
    {
        "technique_id": "mlsd_recommender_feedback_loop",
        "name": "Feedback Loop Detection in Recommender and Ranking Systems",
        "origin_company": "Netflix / YouTube / Airbnb",
        "source_url": "https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
        "domain_tags": ["AIInfra", "MLOps", "WebScale"],
        "design_techniques": [
            "Diversity injection — force exploration of non-clicked content",
            "Counterfactual logging for unbiased offline evaluation",
            "Exposure correction — down-weight items amplified by the model itself",
            "Separate optimisation targets for engagement vs satisfaction metrics",
        ],
        "positive_outcomes": [
            "Netflix separates short-term engagement (clicks) from long-term satisfaction (hours watched)",
            "Exploration budget prevents popular-item concentration and cold-start starvation",
            "Counterfactual evaluation enables offline A/B testing without serving biased data",
        ],
        "negative_side_effects": [
            "Diversity injection reduces short-term click-through rate — requires executive buy-in",
            "Counterfactual logging infrastructure is complex to implement correctly",
            "Feedback loop detection requires long observation windows — weeks to months",
        ],
        "counter_indicators": [
            "Non-personalised ranking systems with no user feedback loop",
            "Search systems where relevance is grounded in explicit query intent not past behaviour",
        ],
        "scale_context": {
            "team_size_min": 4,
        },
    },
    {
        "technique_id": "mlsd_offline_online_eval_gap",
        "name": "Offline-Online Evaluation Gap — Why Offline Metrics Lie",
        "origin_company": "DoorDash / Instacart / Wayfair",
        "source_url": "https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
        "domain_tags": ["AIInfra", "MLOps"],
        "design_techniques": [
            "Online A/B testing as the ground truth signal",
            "Interleaving tests for faster ranking evaluation",
            "Holdout sets with temporal splits (not random) to avoid data leakage",
            "Production shadow scoring to measure real latency vs offline estimate",
        ],
        "positive_outcomes": [
            "DoorDash found their offline AUC improvements did not predict delivery time reductions",
            "Temporal train/test split prevented 20% optimistic bias in offline evaluation",
            "Shadow scoring revealed 3x inference latency gap between benchmark and production",
        ],
        "negative_side_effects": [
            "Online A/B tests require weeks of traffic to reach statistical significance",
            "Interleaving tests require platform support for mixed result serving",
            "Random train/test splits cause data leakage — models look better offline than they are",
        ],
        "counter_indicators": [
            "Systems with extremely low traffic where A/B testing is not statistically feasible",
            "Safety-critical models where online experimentation carries unacceptable risk",
        ],
        "scale_context": {
            "team_size_min": 2,
        },
    },
    {
        "technique_id": "mlsd_batch_vs_realtime_inference",
        "name": "Batch vs Real-Time Inference Routing for ML Serving",
        "origin_company": "Uber / Airbnb / LinkedIn",
        "source_url": "https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
        "domain_tags": ["AIInfra", "MLOps"],
        "design_techniques": [
            "Pre-computed batch predictions cached in feature store or Redis",
            "Real-time inference with model server (TorchServe, TF Serving, Triton)",
            "Hybrid: batch for cold-start, real-time for personalisation",
            "Request-time feature freshness SLA — determines which path is required",
        ],
        "positive_outcomes": [
            "Batch inference reduces p99 latency from 200ms to <5ms for pre-computable predictions",
            "Uber serves 95% of ride-pricing predictions from pre-computed batch cache",
            "Real-time path reserved only for features that change within the request window",
        ],
        "negative_side_effects": [
            "Batch predictions go stale — staleness window must be acceptable to business",
            "Cache invalidation complexity grows with number of features and user segments",
            "Wrong routing choice (batch for real-time use case) causes accuracy degradation at scale",
        ],
        "counter_indicators": [
            "Predictions that depend on real-time context that cannot be pre-computed (live inventory, current location)",
            "Low-volume use cases where batch overhead is not justified",
        ],
        "scale_context": {
            "team_size_min": 2,
        },
    },
    {
        "technique_id": "mlsd_fraud_detection_latency",
        "name": "Real-Time Fraud Detection — Latency vs Accuracy Tradeoff",
        "origin_company": "Stripe / PayPal / Instacart",
        "source_url": "https://github.com/Engineer1999/A-Curated-List-of-ML-System-Design-Case-Studies",
        "domain_tags": ["AIInfra", "MLOps", "Finance", "Security"],
        "design_techniques": [
            "Two-stage scoring: fast rule engine (<1ms) + slow ML model (<100ms)",
            "Feature freshness tiering: real-time features (last 60s) vs batch features (last 24h)",
            "Async model scoring with synchronous rule gate for payment-critical paths",
            "False-positive budget allocation — acceptable block rate vs fraud prevention tradeoff",
        ],
        "positive_outcomes": [
            "Stripe's two-stage approach blocks 99.9% of known fraud patterns in <5ms",
            "Rule engine handles high-confidence cases; ML model handles edge cases",
            "Feature freshness tiering allows sub-100ms ML scoring with minimal staleness",
        ],
        "negative_side_effects": [
            "Two-stage systems require synchronisation of rule engine and ML model thresholds",
            "Real-time feature computation for fraud adds significant infrastructure cost",
            "False-positive rate increase with stricter thresholds causes legitimate transaction failures",
        ],
        "counter_indicators": [
            "Low-value transactions where fraud risk does not justify real-time ML cost",
            "B2B payment flows with manual review steps where async scoring is acceptable",
        ],
        "scale_context": {
            "team_size_min": 3,
        },
    },
]
