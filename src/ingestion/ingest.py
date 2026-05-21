import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.ingestion.resume_parser import parse_resume


def ingest_resumes(
    csv_path: str,
    output_path: str,
    limit: int | None = None,
    skip_errors: bool = True,
) -> int:
    start = time.perf_counter()
    processed = 0
    errors = 0
    candidates = []

    print(f"Ingesting resumes from: {csv_path}")
    print(f"Output to: {output_path}")

    line_count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"CSV headers: {header}")

        for row in reader:
            line_count += 1
            if limit and processed >= limit:
                break

            try:
                parsed = parse_resume(row)
                if parsed:
                    candidates.append(parsed)
                    processed += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                if not skip_errors:
                    raise
                continue

            if processed > 0 and processed % 200 == 0:
                print(f"  Processed {processed} resumes...")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)

    elapsed = time.perf_counter() - start
    print(f"\nDone in {elapsed:.2f}s")
    print(f"Total CSV lines (excl header): {line_count}")
    print(f"Successfully parsed: {processed}")
    print(f"Errors/skipped: {errors}")
    print(f"Output file: {output_path} ({os.path.getsize(output_path) / 1024:.1f} KB)")

    return processed


if __name__ == "__main__":
    csv_path = "C:\\Users\\vmuser\\Documents\\ProdaptCapstone\\data\\raw\\Resume.csv"
    output_path = "C:\\Users\\vmuser\\Documents\\ProdaptCapstone\\data\\processed\\resumes.json"

    ingest_resumes(csv_path, output_path)
