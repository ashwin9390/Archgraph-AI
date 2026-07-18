"""
ArchGraph AI — Full Test Suite
55 tests across 10 suites. All run offline, no internet, no Neo4j required.

Run:
    cd archgraph-ai
    python tests/test_archgraph.py -v
    python -m pytest tests/ -v   (if pytest installed)
"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Stub aiohttp — not needed for tests, not available in all environments
import types
_aio = types.ModuleType('aiohttp')
class _T:
    def __init__(self, **k): pass
class _CS:
    def __init__(self, **k): pass
_aio.ClientTimeout = _T
_aio.ClientSession = _CS
sys.modules.setdefault('aiohttp', _aio)

from archgraph.graph.graph_manager import InMemoryGraph, create_graph
from archgraph.graph.seed_data import SEED_TECHNIQUES
from archgraph.critic.engine import (
    ArchitectureInput, CriticEngine,
    RISK_CRITICAL, RISK_WARNING, RISK_OK,
)
from archgraph.ingestion.fetcher import DOMAIN_REGISTRY, resolve_domain_tags


def _make_engine():
    g = InMemoryGraph()
    g.load_seed_data(SEED_TECHNIQUES)
    return CriticEngine(g), g


def crit(text, engine):
    return engine.critique(ArchitectureInput.from_text(text))


# ─────────────────────────────────────────────────────────────────────────────
class TestIngestion(unittest.TestCase):
    def test_domain_registry_not_empty(self):
        self.assertGreater(len(DOMAIN_REGISTRY), 10)

    def test_discord_resolves_to_realtime(self):
        tags = resolve_domain_tags("https://discord.com/blog/how-discord-stores-messages")
        self.assertIn("RealTime", tags)

    def test_unknown_domain_returns_unknown(self):
        self.assertEqual(resolve_domain_tags("https://random.io/post"), ["Unknown"])


# ─────────────────────────────────────────────────────────────────────────────
class TestInMemoryGraph(unittest.TestCase):
    def setUp(self):
        self.g = InMemoryGraph()
        self.g.load_seed_data(SEED_TECHNIQUES)

    def test_seed_count(self):
        self.assertEqual(self.g.stats()["total_techniques"], 17)

    def test_kafka_query(self):
        self.assertGreater(len(self.g.query_by_stack(["kafka"])), 0)

    def test_aiinfra_domain_has_ml_techniques(self):
        results = self.g.query_by_domain("AIInfra")
        self.assertGreaterEqual(len(results), 5)

    def test_medtech_domain_filter(self):
        results = self.g.query_by_domain("MedTech")
        self.assertTrue(all("MedTech" in r["domain_tags"] for r in results))

    def test_unknown_keyword_empty(self):
        self.assertEqual(self.g.query_by_stack(["xyzzy_nonexistent"]), [])

    def test_deduplication(self):
        self.g.add_technique(SEED_TECHNIQUES[0])
        self.assertEqual(self.g.stats()["total_techniques"], 17)

    def test_create_graph_fallback(self):
        g = create_graph()
        self.assertEqual(g.stats()["backend"], "in-memory")


# ─────────────────────────────────────────────────────────────────────────────
class TestArchitectureInputParser(unittest.TestCase):
    def test_team_size_extracted(self):
        a = ArchitectureInput.from_text("3 backend engineers using kafka")
        self.assertEqual(a.team_size, 3)

    def test_wps_extracted(self):
        a = ArchitectureInput.from_text("60,000 writes/sec kafka")
        self.assertEqual(a.writes_per_second, 60000)

    def test_kafka_in_keywords(self):
        a = ArchitectureInput.from_text("kafka cassandra redis 5 engineers")
        self.assertIn("kafka", a.stack_keywords)

    def test_medtech_domain(self):
        self.assertEqual(
            ArchitectureInput.from_text("patient vitals HIPAA websocket").domain, "MedTech")

    def test_finance_domain(self):
        self.assertEqual(
            ArchitectureInput.from_text("stripe payment transactions").domain, "Finance")

    def test_aiinfra_domain(self):
        self.assertEqual(
            ArchitectureInput.from_text("LLM agent pipeline sequential").domain, "AIInfra")


# ─────────────────────────────────────────────────────────────────────────────
class TestOperationalRules(unittest.TestCase):
    def setUp(self):
        self.engine, _ = _make_engine()

    def test_kafka_small_team_critical(self):
        r = crit("self-managed kafka 3 engineers 60k writes/sec", self.engine)
        self.assertEqual(r.overall_risk, RISK_CRITICAL)

    def test_kafka_large_team_no_critical(self):
        r = crit("kafka 20 engineers 60k writes/sec", self.engine)
        kafka_crits = [i for i in r.items
                       if "kafka" in i.title.lower() and i.risk_level == RISK_CRITICAL]
        self.assertEqual(kafka_crits, [])

    def test_cassandra_small_team_critical(self):
        r = crit("cassandra self-managed 3 engineers", self.engine)
        self.assertEqual(r.overall_risk, RISK_CRITICAL)

    def test_medtech_websocket_critical(self):
        r = crit("websocket patient vitals monitoring centralized cloud 4 engineers", self.engine)
        self.assertEqual(r.overall_risk, RISK_CRITICAL)

    def test_payment_idempotency_detected(self):
        r = crit("payment transaction API REST postgres 5 engineers", self.engine)
        self.assertTrue(any("idempotency" in i.title.lower() for i in r.items))

    def test_payment_idempotency_suppressed(self):
        r = crit("payment with idempotency keys deduplication 5 engineers", self.engine)
        self.assertFalse(any("idempotency" in i.title.lower() for i in r.items))


# ─────────────────────────────────────────────────────────────────────────────
class TestDesignIssues(unittest.TestCase):
    def setUp(self):
        self.engine, _ = _make_engine()

    def test_circuit_breaker_detected(self):
        r = crit("microservice REST API postgres 5 engineers", self.engine)
        self.assertTrue(any("circuit" in i.title.lower() for i in r.items))

    def test_circuit_breaker_suppressed(self):
        r = crit("microservice REST API with circuit breaker hystrix 5 engineers", self.engine)
        self.assertFalse(any("circuit" in i.title.lower() for i in r.items))

    def test_rate_limiting_detected(self):
        r = crit("REST API public postgres 5 engineers", self.engine)
        self.assertTrue(any("rate" in i.title.lower() for i in r.items))

    def test_rate_limiting_suppressed(self):
        r = crit("REST API with rate limiting throttling 5 engineers", self.engine)
        self.assertFalse(any(
            "rate limit" in i.title.lower() or "abuse" in i.title.lower()
            for i in r.items))

    def test_caching_detected(self):
        r = crit("postgres REST API backend 5 engineers", self.engine)
        self.assertTrue(any("cach" in i.title.lower() for i in r.items))

    def test_caching_suppressed(self):
        r = crit("postgres REST API with redis cache 5 engineers", self.engine)
        self.assertFalse(any("cach" in i.title.lower() for i in r.items))

    def test_single_db_detected(self):
        r = crit("postgres single primary REST API 5 engineers", self.engine)
        self.assertTrue(any(
            "failover" in i.title.lower() or "single" in i.title.lower()
            for i in r.items))

    def test_single_db_suppressed(self):
        r = crit("postgres multi-az replica failover REST API 5 engineers", self.engine)
        self.assertFalse(any("failover" in i.title.lower() for i in r.items))

    def test_no_retry_detected(self):
        r = crit("microservice REST API downstream calls 5 engineers postgres", self.engine)
        self.assertTrue(any(
            "retry" in i.title.lower() or "timeout" in i.title.lower()
            for i in r.items))

    def test_retry_suppressed(self):
        r = crit("microservice REST API with retry timeout backoff 5 engineers", self.engine)
        self.assertFalse(any("retry" in i.title.lower() for i in r.items))

    def test_sync_chain_detected(self):
        r = crit("microservice sequential chain service-to-service calls 5 engineers", self.engine)
        self.assertTrue(any(
            "synchronous" in i.title.lower() or "chain" in i.title.lower()
            for i in r.items))

    def test_sync_chain_suppressed_by_async(self):
        r = crit("microservice async event queue kafka 5 engineers", self.engine)
        self.assertFalse(any("synchronous" in i.title.lower() for i in r.items))

    def test_llm_agent_chain_detected(self):
        r = crit("sequential agent chain pipeline llm 5 engineers", self.engine)
        self.assertTrue(any(
            "agent" in i.title.lower() or "sequential" in i.title.lower()
            for i in r.items))

    def test_cdn_detected(self):
        r = crit("react frontend static assets public web 5 engineers", self.engine)
        self.assertTrue(any("cdn" in i.title.lower() for i in r.items))

    def test_cdn_suppressed(self):
        r = crit("react frontend with cloudfront cdn 5 engineers", self.engine)
        self.assertFalse(any("cdn" in i.title.lower() for i in r.items))

    def test_load_balancer_detected(self):
        r = crit("microservice kubernetes docker multiple replicas 5 engineers", self.engine)
        self.assertTrue(any("load balanc" in i.title.lower() for i in r.items))

    def test_load_balancer_suppressed(self):
        r = crit("microservice kubernetes nginx ingress load balancer 5 engineers", self.engine)
        self.assertFalse(any("load balanc" in i.title.lower() for i in r.items))

    def test_cap_violation_detected(self):
        r = crit("payment ledger cassandra eventual consistency 5 engineers", self.engine)
        self.assertTrue(any("cap" in i.title.lower() for i in r.items))

    def test_cap_suppressed_with_acid(self):
        r = crit("payment ledger postgres acid serializable 5 engineers", self.engine)
        self.assertFalse(any("cap" in i.title.lower() for i in r.items))

    def test_dlq_detected(self):
        r = crit("event-driven kafka consumer 5 engineers", self.engine)
        self.assertTrue(any(
            "dead-letter" in i.title.lower() or "dlq" in i.title.lower()
            for i in r.items))

    def test_dlq_suppressed(self):
        r = crit("event-driven kafka consumer with dead letter queue dlq 5 engineers", self.engine)
        self.assertFalse(any(
            "dead-letter" in i.title.lower() or "dlq" in i.title.lower()
            for i in r.items))

    def test_backpressure_detected(self):
        r = crit("event-driven 100k events kafka consumer 5 engineers", self.engine)
        self.assertTrue(any(
            "backpressure" in i.title.lower() or "consumer lag" in i.title.lower()
            for i in r.items))

    def test_backpressure_suppressed(self):
        r = crit(
            "event-driven kafka consumer with backpressure flow control consumer lag 5 engineers",
            self.engine)
        self.assertFalse(any("backpressure" in i.title.lower() for i in r.items))


# ─────────────────────────────────────────────────────────────────────────────
class TestTeamMaturityRules(unittest.TestCase):
    def setUp(self):
        self.engine, _ = _make_engine()

    def test_new_team_high_scale_critical(self):
        r = crit(
            "event-driven architecture 7 backend engineers 100k events/sec new team",
            self.engine)
        self.assertEqual(r.overall_risk, RISK_CRITICAL)

    def test_new_team_high_scale_multiple_issues(self):
        r = crit(
            "event-driven architecture 7 backend engineers 100k events/sec new team",
            self.engine)
        self.assertGreaterEqual(len(r.items), 3)

    def test_experienced_team_suppressed(self):
        r = crit(
            "event-driven kafka 7 engineers 100k experienced sre runbook on-call",
            self.engine)
        self.assertFalse(any(
            "new team" in i.title.lower() or "high event" in i.title.lower()
            for i in r.items))

    def test_missing_runbook_detected(self):
        r = crit("event-driven kafka 7 engineers 100k new team", self.engine)
        self.assertTrue(any(
            "runbook" in i.title.lower() or "on-call" in i.title.lower()
            for i in r.items))

    def test_runbook_present_suppressed(self):
        r = crit(
            "event-driven kafka 7 engineers 100k runbook on-call incident response",
            self.engine)
        self.assertFalse(any("runbook" in i.title.lower() for i in r.items))

    def test_feature_store_category_design(self):
        r = crit("ml model production inference pytorch 5 engineers", self.engine)
        self.assertTrue(any(i.category == "DESIGN" for i in r.items))

    def test_new_team_category_operational(self):
        r = crit("event-driven 100k new team 7 engineers", self.engine)
        self.assertTrue(any(i.category == "OPERATIONAL" for i in r.items))


# ─────────────────────────────────────────────────────────────────────────────
class TestSecurityIssues(unittest.TestCase):
    def setUp(self):
        self.engine, _ = _make_engine()

    def test_no_auth_detected(self):
        r = crit("REST API public endpoint postgres 5 engineers", self.engine)
        self.assertTrue(any("auth" in i.title.lower() for i in r.items))

    def test_auth_suppressed(self):
        r = crit("REST API with oauth jwt authentication 5 engineers", self.engine)
        self.assertFalse(any("auth" in i.title.lower() for i in r.items))

    def test_no_tls_detected(self):
        r = crit("REST API internal microservice service calls 5 engineers", self.engine)
        self.assertTrue(any(
            "tls" in i.title.lower() or "encrypt" in i.title.lower()
            for i in r.items))

    def test_tls_suppressed(self):
        r = crit("REST API https tls ssl microservice 5 engineers", self.engine)
        self.assertFalse(any("tls" in i.title.lower() for i in r.items))


# ─────────────────────────────────────────────────────────────────────────────
class TestObservabilityGaps(unittest.TestCase):
    def setUp(self):
        self.engine, _ = _make_engine()

    def test_no_observability_detected(self):
        r = crit("microservice kubernetes postgres 5 engineers", self.engine)
        self.assertTrue(any("observ" in i.title.lower() for i in r.items))

    def test_observability_suppressed(self):
        r = crit(
            "microservice kubernetes prometheus grafana opentelemetry 5 engineers",
            self.engine)
        self.assertFalse(any("observ" in i.title.lower() for i in r.items))


class TestMLInfrastructureRules(unittest.TestCase):
    def setUp(self):
        self.engine, _ = _make_engine()

    def test_feature_store_missing_critical(self):
        r = crit("ml model inference pytorch tensorflow production 5 engineers", self.engine)
        self.assertTrue(any(
            "feature store" in i.title.lower() or "skew" in i.title.lower()
            for i in r.items))

    def test_feature_store_present_suppressed(self):
        r = crit(
            "ml model with feature store feast online offline parity 5 engineers",
            self.engine)
        self.assertFalse(any("skew" in i.title.lower() for i in r.items))

    def test_no_model_versioning_critical(self):
        r = crit("ml model deploy production inference 5 engineers", self.engine)
        self.assertTrue(any(
            "version" in i.title.lower() or "rollback" in i.title.lower()
            for i in r.items))

    def test_model_versioning_present_suppressed(self):
        r = crit(
            "ml model deploy with shadow canary rollback mlflow model registry 5 engineers",
            self.engine)
        self.assertFalse(any(
            "version" in i.title.lower() or "rollback" in i.title.lower()
            for i in r.items))

    def test_recommender_feedback_loop_detected(self):
        r = crit("recommender system ranking feed personalisation 5 engineers", self.engine)
        self.assertTrue(any(
            "feedback" in i.title.lower() or "popularity" in i.title.lower()
            for i in r.items))

    def test_feedback_loop_suppressed(self):
        r = crit(
            "recommender with exploration diversity counterfactual feedback loop 5 engineers",
            self.engine)
        self.assertFalse(any("feedback" in i.title.lower() for i in r.items))

    def test_batch_inference_warning(self):
        r = crit("batch inference nightly scheduled prediction 5 engineers", self.engine)
        self.assertTrue(any(
            "batch" in i.title.lower() or "staleness" in i.title.lower()
            for i in r.items))

    def test_batch_inference_suppressed(self):
        r = crit(
            "batch inference with real-time latency sla p99 model server triton 5 engineers",
            self.engine)
        self.assertFalse(any(
            "batch" in i.title.lower() and "staleness" in i.title.lower()
            for i in r.items))

    def test_feature_store_category_is_design(self):
        r = crit("ml model production inference pytorch 5 engineers", self.engine)
        self.assertTrue(any(
            i.category == "DESIGN" and "skew" in i.title.lower()
            for i in r.items))

    def test_model_versioning_category_is_operational(self):
        r = crit("ml model deploy production inference 5 engineers", self.engine)
        self.assertTrue(any(
            i.category == "OPERATIONAL" and "version" in i.title.lower()
            for i in r.items))


# ─────────────────────────────────────────────────────────────────────────────
class TestCategoryTagging(unittest.TestCase):
    def setUp(self):
        self.engine, _ = _make_engine()

    def test_operational_category(self):
        r = crit("self-managed kafka 3 engineers", self.engine)
        self.assertTrue(any(i.category == "OPERATIONAL" for i in r.items))

    def test_design_category(self):
        r = crit("microservice REST API postgres 5 engineers", self.engine)
        self.assertTrue(any(i.category == "DESIGN" for i in r.items))

    def test_security_category(self):
        r = crit("REST API public endpoint postgres 5 engineers", self.engine)
        self.assertTrue(any(i.category == "SECURITY" for i in r.items))

    def test_observability_category(self):
        r = crit("microservice kubernetes postgres 5 engineers", self.engine)
        self.assertTrue(any(i.category == "OBSERVABILITY" for i in r.items))


# ─────────────────────────────────────────────────────────────────────────────
class TestFullyAddressedArchitecture(unittest.TestCase):
    def setUp(self):
        self.engine, _ = _make_engine()

    def test_all_fixes_present_gives_ok(self):
        r = crit(
            "postgres multi-az replica redis cache REST API https oauth jwt "
            "prometheus grafana opentelemetry retry timeout backoff circuit breaker "
            "rate limiting nginx ingress load balancer 10 engineers",
            self.engine)
        self.assertEqual(r.overall_risk, RISK_OK)

    def test_all_fixes_zero_issues(self):
        r = crit(
            "postgres multi-az replica redis cache REST API https oauth jwt "
            "prometheus grafana opentelemetry retry timeout backoff circuit breaker "
            "rate limiting nginx ingress load balancer 10 engineers",
            self.engine)
        self.assertEqual(len(r.items), 0)


# ─────────────────────────────────────────────────────────────────────────────
class TestDesignBlueprint(unittest.TestCase):
    def setUp(self):
        self.engine, _ = _make_engine()

    def test_blueprint_present_on_report(self):
        r = crit("microservice REST API postgres kafka 5 engineers", self.engine)
        self.assertIsNotNone(r.blueprint)

    def test_blueprint_has_layers(self):
        r = crit("microservice REST API postgres kafka 5 engineers", self.engine)
        self.assertGreater(len(r.blueprint.layers), 0)

    def test_blueprint_has_checklist_when_issues_found(self):
        r = crit("microservice REST API postgres 5 engineers", self.engine)
        self.assertGreater(len(r.blueprint.checklist), 0)

    def test_blueprint_checklist_empty_when_fully_fixed(self):
        r = crit(
            "postgres multi-az replica redis cache REST API https oauth jwt "
            "prometheus grafana opentelemetry retry timeout backoff circuit breaker "
            "rate limiting nginx ingress load balancer microservice runbook on-call "
            "incident response 10 engineers",
            self.engine)
        self.assertEqual(len(r.blueprint.checklist), 0)

    def test_blueprint_anti_patterns_match_issues(self):
        r = crit("microservice REST API postgres 5 engineers", self.engine)
        self.assertGreater(len(r.blueprint.anti_patterns), 0)

    def test_blueprint_layer_marked_ok_when_fixed(self):
        r = crit(
            "microservice REST API with circuit breaker hystrix retry timeout "
            "backoff 5 engineers",
            self.engine)
        service_layer = next(
            (l for l in r.blueprint.layers if l.layer == "Service Layer"), None
        )
        self.assertIsNotNone(service_layer)
        self.assertIn("✅", service_layer.component)

    def test_blueprint_layer_shows_gap_when_missing(self):
        r = crit("microservice REST API postgres 5 engineers", self.engine)
        service_layer = next(
            (l for l in r.blueprint.layers if l.layer == "Service Layer"), None
        )
        self.assertIsNotNone(service_layer)
        self.assertIn("⚠️", service_layer.component)

    def test_blueprint_includes_data_layer_when_db_mentioned(self):
        r = crit("postgres REST API 5 engineers", self.engine)
        self.assertTrue(any(l.layer == "Data Layer" for l in r.blueprint.layers))

    def test_blueprint_includes_messaging_layer_when_kafka_mentioned(self):
        r = crit("kafka event-driven consumer 5 engineers", self.engine)
        self.assertTrue(any(l.layer == "Messaging / Event Layer" for l in r.blueprint.layers))

    def test_blueprint_includes_ml_layer_when_ml_mentioned(self):
        r = crit("ml model pytorch inference production 5 engineers", self.engine)
        self.assertTrue(any(l.layer == "ML Infrastructure Layer" for l in r.blueprint.layers))

    def test_blueprint_includes_medtech_layer_for_medtech_domain(self):
        r = crit("websocket patient vitals monitoring 4 engineers", self.engine)
        self.assertTrue(any("MedTech" in l.layer for l in r.blueprint.layers))

    def test_blueprint_observability_layer_always_present(self):
        r = crit("postgres REST API 5 engineers", self.engine)
        self.assertTrue(any(l.layer == "Observability Layer" for l in r.blueprint.layers))

    def test_blueprint_render_text_contains_header(self):
        r = crit("microservice REST API postgres 5 engineers", self.engine)
        self.assertIn("Recommended Best Design", r.blueprint.render_text())

    def test_blueprint_render_text_contains_checklist_section(self):
        r = crit("microservice REST API postgres 5 engineers", self.engine)
        self.assertIn("IMPLEMENTATION CHECKLIST", r.blueprint.render_text())

    def test_blueprint_render_dict_keys(self):
        r = crit("microservice REST API postgres 5 engineers", self.engine)
        d = r.blueprint.render_dict()
        self.assertIn("layers", d)
        self.assertIn("checklist", d)
        self.assertIn("anti_patterns", d)
        self.assertIn("citations", d)

    def test_full_report_render_dict_includes_best_design(self):
        r = crit("microservice REST API postgres 5 engineers", self.engine)
        d = r.render_dict()
        self.assertIn("best_design", d)

    def test_full_report_render_text_includes_blueprint(self):
        r = crit("microservice REST API postgres 5 engineers", self.engine)
        self.assertIn("Recommended Best Design", r.render_text())

    def test_blueprint_citations_are_deduplicated(self):
        r = crit("microservice REST API postgres kafka 5 engineers", self.engine)
        citations = r.blueprint.citations
        self.assertEqual(len(citations), len(set(citations)))


# ─────────────────────────────────────────────────────────────────────────────
class TestRenderOutput(unittest.TestCase):
    def setUp(self):
        self.engine, _ = _make_engine()
        self.report = crit(
            "kafka cassandra 3 engineers microservice REST API postgres", self.engine)

    def test_render_text_has_header(self):
        self.assertIn("ArchGraph AI", self.report.render_text())

    def test_render_text_has_all_sections(self):
        txt = self.report.render_text()
        for section in ["OPERATIONAL", "DESIGN", "SECURITY", "OBSERVABILITY"]:
            self.assertIn(section, txt)

    def test_render_dict_keys(self):
        d = self.report.render_dict()
        self.assertIn("critique_items", d)
        self.assertIn("overall_risk", d)

    def test_all_items_have_category(self):
        d = self.report.render_dict()
        self.assertTrue(all("category" in i for i in d["critique_items"]))

    def test_all_items_have_citations(self):
        d = self.report.render_dict()
        self.assertTrue(all("citations" in i for i in d["critique_items"]))

    def test_all_items_have_risk_level(self):
        d = self.report.render_dict()
        self.assertTrue(all("risk_level" in i for i in d["critique_items"]))


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    verbosity = 2 if "-v" in sys.argv else 1
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [
        TestIngestion, TestInMemoryGraph, TestArchitectureInputParser,
        TestOperationalRules, TestDesignIssues, TestTeamMaturityRules,
        TestMLInfrastructureRules, TestSecurityIssues, TestObservabilityGaps,
        TestCategoryTagging, TestFullyAddressedArchitecture,
        TestDesignBlueprint, TestRenderOutput,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
