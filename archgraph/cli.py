"""
ArchGraph AI — CLI
Usage:
  archgraph critique "kafka + cassandra, 2 engineers, 60k writes/sec"
  archgraph critique --domain MedTech "websocket vitals monitoring, 4 engineers"
  archgraph list-techniques
  archgraph stats
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")


def _build_graph():
    from archgraph.graph.graph_manager import create_graph
    from archgraph.graph.seed_data import SEED_TECHNIQUES

    uri = os.getenv("NEO4J_URI", "")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    graph = create_graph(uri=uri, user=user, password=password)
    graph.load_seed_data(SEED_TECHNIQUES)
    return graph


def cmd_critique(args):
    from archgraph.critic.engine import ArchitectureInput, CriticEngine

    text = " ".join(args.description)
    arch = ArchitectureInput.from_text(text)
    if args.domain:
        arch.domain = args.domain
    if args.team:
        arch.team_size = args.team

    graph = _build_graph()
    engine = CriticEngine(graph)
    report = engine.critique(arch)
    graph.close()

    if args.json:
        print(json.dumps(report.render_dict(), indent=2))
    else:
        print(report.render_text())


def cmd_list(args):
    graph = _build_graph()
    techniques = graph.get_all_techniques()
    graph.close()
    for t in techniques:
        tid = t.get("technique_id", "?")
        name = t.get("name", "?")
        tags = t.get("domain_tags", [])
        company = t.get("origin_company", "?")
        print(f"  [{tid}]")
        print(f"    Name    : {name}")
        print(f"    Company : {company}")
        print(f"    Tags    : {', '.join(tags)}")
        print()


def cmd_stats(args):
    graph = _build_graph()
    s = graph.stats()
    graph.close()
    print(json.dumps(s, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="archgraph",
        description="ArchGraph AI — Citation-backed architecture critique engine",
    )
    sub = parser.add_subparsers(dest="command")

    # critique
    p_crit = sub.add_parser("critique", help="Critique an architecture description")
    p_crit.add_argument("description", nargs="+", help="Architecture description (free text)")
    p_crit.add_argument("--domain", default=None, help="Force domain: MedTech | Finance | AIInfra | WebScale")
    p_crit.add_argument("--team", type=int, default=None, help="Team size override")
    p_crit.add_argument("--json", action="store_true", help="Output JSON instead of formatted text")
    p_crit.set_defaults(func=cmd_critique)

    # list
    p_list = sub.add_parser("list-techniques", help="List all techniques in the graph")
    p_list.set_defaults(func=cmd_list)

    # stats
    p_stats = sub.add_parser("stats", help="Graph statistics")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
