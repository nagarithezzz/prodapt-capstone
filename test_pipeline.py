import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.pipeline import run_pipeline

test_queries = [
    "We are looking for someone who mainly works on the backend of web applications and has experience building services that connect multiple systems. Familiarity with modern deployment environments would be helpful.",
    "I need someone early in their career who can analyze business data, generate reports, and work with tools used for interpreting datasets.",
    "We are hiring a senior professional who can design large-scale digital systems that run on cloud infrastructure and understands microservice-based architectures.",
    "We are looking for someone who focuses on building the visual and interactive components of web applications to improve user experience.",
    "need a website maker with good design skills",
]

for i, query in enumerate(test_queries):
    print(f"\n{'='*70}")
    print(f"  TEST {i+1}: {query[:80]}...")
    print(f"{'='*70}")

    result = run_pipeline(query, verbose=True)

    if "error" in result:
        print(f"  ERROR: {result['error']}")
        continue

    print(f"\n  Results:")
    for j, r in enumerate(result["results"]):
        print(f"\n    {j+1}. {r['id']}  Score: {r['overall_score']}/100")
        print(f"       Skills: {', '.join(r['skills'][:8])}")
        print(f"       Category: {r['category']}  |  Role: {r['role_category']}")
        print(f"       Justification: {r['justification']}")
        print(f"       (Skill: {r['skill_score']}, Exp: {r['experience_score']})")

    print(f"\n  Requirements extracted:")
    for k, v in result["requirements"].items():
        if k != "original_query":
            print(f"    {k}: {v}")
