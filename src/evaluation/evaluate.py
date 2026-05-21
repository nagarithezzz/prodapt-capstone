import json
import math
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.retrieval.vector_search import search_candidates as vector_search
from src.retrieval.bm25_search import search_bm25
from src.retrieval.hybrid_search import search_hybrid
from src.retrieval.reranker import rerank

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "resumes.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "evaluation_output")

TEST_QUERIES = [
    {"query": "senior Python developer with AWS and Docker", "skills": ["python", "aws", "docker"]},
    {"query": "junior data analyst with SQL and Excel", "skills": ["sql", "excel"]},
    {"query": "frontend React developer with TypeScript", "skills": ["react", "typescript", "javascript"]},
    {"query": "machine learning engineer with Python and TensorFlow", "skills": ["python", "machine learning", "tensorflow"]},
    {"query": "DevOps engineer with Kubernetes and CI/CD", "skills": ["kubernetes", "ci/cd", "docker"]},
    {"query": "Java backend developer with Spring Boot", "skills": ["java", "spring boot"]},
    {"query": "iOS developer with Swift and UIKit", "skills": ["swift", "ios"]},
    {"query": "product manager with agile and stakeholder management", "skills": ["agile", "product management"]},
    {"query": "cybersecurity analyst with network security", "skills": ["cybersecurity", "network security"]},
    {"query": "UX designer with Figma and user research", "skills": ["figma", "ux", "design"]},
]

TOP_K = 5
RETRIEVE_TOP_K = 30

all_candidates: dict[str, dict] = {}


def load_candidates():
    global all_candidates
    if not all_candidates:
        print(f"Loading {DATA_PATH}...")
        with open(DATA_PATH, "r") as f:
            for c in json.load(f):
                all_candidates[c["id"]] = c
        print(f"  Loaded {len(all_candidates)} candidates")


def get_candidate_skills(cid: str) -> list[str]:
    c = all_candidates.get(cid, {})
    raw = c.get("skills", [])
    return [s.lower().strip() for s in raw if isinstance(s, str)]


def is_relevant(cid: str, required_skills: list[str]) -> int:
    cand_skills = get_candidate_skills(cid)
    if not cand_skills or not required_skills:
        return 0
    matches = 0
    for rs in required_skills:
        rs_lower = rs.lower()
        for cs in cand_skills:
            if rs_lower in cs or cs in rs_lower:
                matches += 1
                break
    threshold = max(1, math.ceil(len(required_skills) * 0.4))
    return 1 if matches >= threshold else 0


def get_all_relevant(required_skills: list[str]) -> set[str]:
    relevant = set()
    for cid in all_candidates:
        if is_relevant(cid, required_skills):
            relevant.add(cid)
    return relevant


def precision_at_k(results: list[str], relevant: set[str], k: int) -> float:
    if k == 0:
        return 0.0
    top_k = results[:k]
    if not top_k:
        return 0.0
    return sum(1 for cid in top_k if cid in relevant) / k


def recall_at_k(results: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = results[:k]
    if not top_k:
        return 0.0
    return sum(1 for cid in top_k if cid in relevant) / len(relevant)


def mrr(results: list[str], relevant: set[str]) -> float:
    for i, cid in enumerate(results):
        if cid in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(results: list[str], relevant: set[str], k: int) -> float:
    top_k = results[:k]
    if not top_k:
        return 0.0
    dcg = 0.0
    for i, cid in enumerate(top_k):
        rel = 1.0 if cid in relevant else 0.0
        dcg += (2**rel - 1) / math.log2(i + 2)
    ideal = sorted(
        [1 if cid in relevant else 0 for cid in top_k], reverse=True
    )
    idcg = sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def run_vector_only(query_text: str, top_k: int = TOP_K) -> list[str]:
    results = vector_search(query_text, top_k=RETRIEVE_TOP_K)
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return [c["id"] for c in results[:top_k]]


def run_hybrid(query_text: str, top_k: int = TOP_K) -> list[str]:
    results = search_hybrid(query_text, top_k=top_k, vector_top_k=RETRIEVE_TOP_K, bm25_top_k=RETRIEVE_TOP_K)
    return [c["id"] for c in results[:top_k]]


def run_reranked(query_text: str, top_k: int = TOP_K) -> list[str]:
    hybrid_results = search_hybrid(query_text, top_k=RETRIEVE_TOP_K, vector_top_k=RETRIEVE_TOP_K, bm25_top_k=RETRIEVE_TOP_K)
    reranked = rerank(query_text, hybrid_results, top_k=top_k)
    return [c["id"] for c in reranked[:top_k]]


def print_results_table(results_by_config: dict, header: str):
    print(f"\n{'='*80}")
    print(f"  {header}")
    print(f"{'='*80}")
    print(f"{'Query':<40} {'P@3':>6} {'P@5':>6} {'R@3':>6} {'R@5':>6} {'MRR':>6} {'nDCG@5':>8}")
    print(f"{'-'*40} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*8}")
    for qname, metrics in results_by_config.items():
        print(f"{qname:<40} {metrics['p3']:>6.3f} {metrics['p5']:>6.3f} {metrics['r3']:>6.3f} {metrics['r5']:>6.3f} {metrics['mrr']:>6.3f} {metrics['ndcg5']:>8.4f}")
    print(f"{'-'*40} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*8}")
    avg = {
        k: np.mean([m[k] for m in results_by_config.values()])
        for k in ["p3", "p5", "r3", "r5", "mrr", "ndcg5"]
    }
    print(f"{'AVERAGE':<40} {avg['p3']:>6.3f} {avg['p5']:>6.3f} {avg['r3']:>6.3f} {avg['r5']:>6.3f} {avg['mrr']:>6.3f} {avg['ndcg5']:>8.4f}")
    print()


def plot_comparison(all_data: dict):
    configs = list(all_data.keys())
    metrics_names = ["P@3", "P@5", "R@3", "R@5", "MRR", "nDCG@5"]
    metric_keys = ["p3", "p5", "r3", "r5", "mrr", "ndcg5"]

    x = np.arange(len(metrics_names))
    width = 0.25
    n_configs = len(configs)

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ["#4ECDC4", "#FF6B6B", "#45B7D1"]
    for i, config in enumerate(configs):
        values = [np.mean([q[mk] for q in all_data[config].values()]) for mk in metric_keys]
        offset = (i - (n_configs - 1) / 2) * width
        bars = ax.bar(x + offset, values, width, label=config, color=colors[i % len(colors)])
        for bar, v in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f"{v:.3f}", ha="center", va="bottom", fontsize=8)

    ax.set_xlabel("Metric", fontsize=12)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title("Retrieval Quality Comparison", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_names, fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, "retrieval_comparison.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    print(f"Chart saved to {path}")


def main():
    print("=" * 80)
    print("  RESUME INTELLIGENCE — RETRIEVAL EVALUATION")
    print("=" * 80)

    load_candidates()

    overall_start = time.perf_counter()

    all_relevant_sets = {}
    print(f"\nComputing relevance labels for {len(TEST_QUERIES)} queries...")
    t1 = time.perf_counter()
    for q in TEST_QUERIES:
        relevant = get_all_relevant(q["skills"])
        all_relevant_sets[q["query"]] = relevant
        print(f"  \"{q['query'][:50]:50s}\" → {len(relevant)} relevant candidates")
    print(f"  Done in {time.perf_counter() - t1:.1f}s")

    configs = {
        "Vector Only": run_vector_only,
        "Hybrid (Vec+BM25)": run_hybrid,
        "Hybrid + Rerank": run_reranked,
    }

    all_data = {}
    for config_name, run_fn in configs.items():
        print(f"\n{'─'*80}")
        print(f"  Running: {config_name}")
        print(f"{'─'*80}")

        results_by_query = {}
        query_times = []

        for q in TEST_QUERIES:
            t1 = time.perf_counter()
            candidate_ids = run_fn(q["query"])
            elapsed = time.perf_counter() - t1
            query_times.append(elapsed)

            relevant = all_relevant_sets[q["query"]]
            results_by_query[q["query"]] = {
                "p3": precision_at_k(candidate_ids, relevant, 3),
                "p5": precision_at_k(candidate_ids, relevant, 5),
                "r3": recall_at_k(candidate_ids, relevant, 3),
                "r5": recall_at_k(candidate_ids, relevant, 5),
                "mrr": mrr(candidate_ids, relevant),
                "ndcg5": ndcg_at_k(candidate_ids, relevant, 5),
            }

            rel_count = sum(1 for cid in candidate_ids if cid in relevant)
            print(f"  [{elapsed:5.1f}s] \"{q['query'][:45]:45s}\" → "
                  f"{rel_count}/{len(candidate_ids)} relevant "
                  f"| P@5={results_by_query[q['query']]['p5']:.3f}")

        print_results_table(results_by_query, f"{config_name} — Average time: {np.mean(query_times):.1f}s")
        all_data[config_name] = results_by_query

    print(f"\nTotal evaluation time: {time.perf_counter() - overall_start:.1f}s")

    plot_comparison(all_data)

    print(f"\nEvaluation report also available in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
