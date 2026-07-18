"""
ArchGraph AI — Graph Layer
Manages Neo4j connection, schema bootstrap, seed loading, and Cypher queries.
Works with a local Neo4j instance OR Neo4j Aura (cloud).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("archgraph.graph")


def _neo4j_available() -> bool:
    try:
        import neo4j  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# In-memory fallback (no Neo4j required for demo/testing)
# ---------------------------------------------------------------------------
class InMemoryGraph:
    """
    Pure-Python fallback graph. Supports the same query API as Neo4jGraph.
    Perfect for CI, demos, and contributors who don't have Neo4j installed.
    """

    def __init__(self) -> None:
        self._techniques: list[dict] = []
        self._loaded = False

    def load_seed_data(self, techniques: list[dict]) -> None:
        self._techniques = techniques
        self._loaded = True
        logger.info("InMemoryGraph: loaded %d seed techniques.", len(techniques))

    def add_technique(self, technique: dict) -> None:
        # Deduplicate by technique_id
        existing_ids = {t["technique_id"] for t in self._techniques}
        if technique.get("technique_id") not in existing_ids:
            self._techniques.append(technique)

    def query_by_stack(self, stack_keywords: list[str], domain_filter: Optional[str] = None) -> list[dict]:
        results = []
        kw_lower = [k.lower() for k in stack_keywords]
        for t in self._techniques:
            text_blob = " ".join([
                t.get("name", ""),
                t.get("origin_company", ""),
                " ".join(t.get("design_techniques", [])),
                " ".join(t.get("counter_indicators", [])),
                " ".join(t.get("positive_outcomes", [])),
            ]).lower()
            if any(kw in text_blob for kw in kw_lower):
                if domain_filter and domain_filter not in t.get("domain_tags", []):
                    continue
                results.append(t)
        return results

    def query_by_domain(self, domain_tag: str) -> list[dict]:
        return [t for t in self._techniques if domain_tag in t.get("domain_tags", [])]

    def get_all_techniques(self) -> list[dict]:
        return list(self._techniques)

    def stats(self) -> dict:
        domains: dict[str, int] = {}
        for t in self._techniques:
            for tag in t.get("domain_tags", []):
                domains[tag] = domains.get(tag, 0) + 1
        return {
            "total_techniques": len(self._techniques),
            "backend": "in-memory",
            "domain_breakdown": domains,
        }

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Neo4j-backed graph
# ---------------------------------------------------------------------------
class Neo4jGraph:
    """
    Wraps Neo4j driver. Falls back gracefully if connection fails.
    Environment variables:
      NEO4J_URI      — default: bolt://localhost:7687
      NEO4J_USER     — default: neo4j
      NEO4J_PASSWORD — default: password
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase  # type: ignore
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._driver.verify_connectivity()
        logger.info("Neo4j connected: %s", uri)
        self._bootstrap_schema()

    def _bootstrap_schema(self) -> None:
        """Create indexes and constraints on first run."""
        with self._driver.session() as session:
            session.run(
                "CREATE CONSTRAINT technique_id IF NOT EXISTS "
                "FOR (t:DesignTechnique) REQUIRE t.technique_id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT company_name IF NOT EXISTS "
                "FOR (c:Company) REQUIRE c.name IS UNIQUE"
            )
            session.run(
                "CREATE INDEX technique_domain IF NOT EXISTS "
                "FOR (t:DesignTechnique) ON (t.domain_tags)"
            )
        logger.info("Neo4j schema bootstrapped.")

    def load_seed_data(self, techniques: list[dict]) -> None:
        with self._driver.session() as session:
            for t in techniques:
                session.run(
                    """
                    MERGE (c:Company {name: $company})
                    MERGE (t:DesignTechnique {technique_id: $tid})
                      ON CREATE SET
                        t.name = $name,
                        t.source_url = $url,
                        t.domain_tags = $tags,
                        t.design_techniques = $dt,
                        t.positive_outcomes = $pos,
                        t.negative_side_effects = $neg,
                        t.counter_indicators = $ci,
                        t.scale_context = $scale
                    MERGE (c)-[:AUTHORED]->(t)
                    """,
                    company=t["origin_company"],
                    tid=t["technique_id"],
                    name=t["name"],
                    url=t["source_url"],
                    tags=t["domain_tags"],
                    dt=t.get("design_techniques", []),
                    pos=t.get("positive_outcomes", []),
                    neg=t.get("negative_side_effects", []),
                    ci=t.get("counter_indicators", []),
                    scale=str(t.get("scale_context", {})),
                )
        logger.info("Neo4j: loaded %d techniques.", len(techniques))

    def add_technique(self, technique: dict) -> None:
        self.load_seed_data([technique])

    def query_by_stack(self, stack_keywords: list[str], domain_filter: Optional[str] = None) -> list[dict]:
        kw_pattern = "|".join(stack_keywords)
        query = """
        MATCH (t:DesignTechnique)
        WHERE any(kw IN $keywords WHERE
              toLower(t.name) CONTAINS toLower(kw)
           OR any(dt IN t.design_techniques WHERE toLower(dt) CONTAINS toLower(kw))
           OR any(ci IN t.counter_indicators WHERE toLower(ci) CONTAINS toLower(kw))
        )
        """ + ("AND $domain IN t.domain_tags " if domain_filter else "") + """
        OPTIONAL MATCH (c:Company)-[:AUTHORED]->(t)
        RETURN t, c.name AS company
        LIMIT 10
        """
        with self._driver.session() as session:
            records = session.run(query, keywords=stack_keywords, domain=domain_filter)
            results = []
            for rec in records:
                node = dict(rec["t"])
                node["origin_company"] = rec["company"]
                results.append(node)
        return results

    def query_by_domain(self, domain_tag: str) -> list[dict]:
        with self._driver.session() as session:
            records = session.run(
                "MATCH (t:DesignTechnique) WHERE $tag IN t.domain_tags RETURN t LIMIT 20",
                tag=domain_tag,
            )
            return [dict(r["t"]) for r in records]

    def get_all_techniques(self) -> list[dict]:
        with self._driver.session() as session:
            records = session.run("MATCH (t:DesignTechnique) RETURN t")
            return [dict(r["t"]) for r in records]

    def stats(self) -> dict:
        with self._driver.session() as session:
            count = session.run("MATCH (t:DesignTechnique) RETURN count(t) AS n").single()["n"]
        return {"total_techniques": count, "backend": "neo4j"}

    def close(self) -> None:
        self._driver.close()


# ---------------------------------------------------------------------------
# Factory — pick Neo4j or fall back to in-memory
# ---------------------------------------------------------------------------
def create_graph(uri: str = "", user: str = "", password: str = "") -> Any:
    """
    Returns a Neo4jGraph if credentials are supplied and neo4j driver is
    installed; otherwise returns InMemoryGraph for zero-dependency operation.
    """
    if uri and _neo4j_available():
        try:
            return Neo4jGraph(uri, user, password)
        except Exception as exc:
            logger.warning("Neo4j connection failed (%s). Using in-memory graph.", exc)
    logger.info("Using in-memory graph backend.")
    return InMemoryGraph()
