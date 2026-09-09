"""
Master pipeline runner.

Runs all phases in order with checkpointing.

Usage:
  python -m src.run_pipeline           # Run all phases
  python -m src.run_pipeline --from 3   # Resume from phase 3
  python -m src.run_pipeline --only 5   # Run only phase 5
"""

import argparse
import json
import sys
import time
from pathlib import Path
from src.config import DATA_RAW, DATA_PROCESSED, DATA_GOLDEN, REPORTS, TABLES, FIGURES, ensure_dirs


PHASES = [
    ("Profile Dataset", "src.profile_dataset",
     lambda: (DATA_PROCESSED / "dataset_profile.json").exists()),
    ("Select Brand", "src.select_brand",
     lambda: (DATA_PROCESSED / "selected_brand.json").exists()),
    ("Build Threads", "src.build_threads",
     lambda: (DATA_PROCESSED / "threads.jsonl").exists()),
    ("Discover Intents", "src.discover_intents",
     lambda: (DATA_PROCESSED / "intent_taxonomy.json").exists()),
    ("Create Golden Set", "src.create_golden_set",
     lambda: (DATA_GOLDEN / "golden_set.csv").exists()),
    ("Majority Baseline", "src.baseline_majority",
     lambda: (TABLES / "baseline_majority.json").exists()),
    ("TF-IDF Baseline", "src.baseline_tfidf",
     lambda: (TABLES / "tfidf_results.json").exists()),
    ("Build Retrieval Index", "src.retrieve_examples",
     lambda: (DATA_PROCESSED / "retrieval_index.pkl").exists()),
    ("Full Evaluation", "src.evaluate",
     lambda: (REPORTS / "results.json").exists()),
    ("Human Agreement", "src.human_judge_agreement",
     lambda: (TABLES / "judge_agreement.json").exists()),
]


def run_phase(name, module_name, check_fn, force=False):
    """Run a single pipeline phase."""
    if not force and check_fn():
        print(f"  ✓ {name} — already complete (use --force to re-run)")
        return True

    print(f"  → Running {name}...")
    start = time.time()

    try:
        import importlib
        mod = importlib.import_module(module_name)
        mod.main()
        elapsed = time.time() - start
        print(f"  ✓ {name} — completed in {elapsed:.1f}s")
        return True
    except SystemExit:
        print(f"  ✗ {name} — exited (likely missing prerequisite)")
        return False
    except Exception as e:
        print(f"  ✗ {name} — failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Run the full pipeline")
    parser.add_argument("--from-phase", type=int, default=1,
                        help="Start from this phase number (1-indexed)")
    parser.add_argument("--only", type=int, default=None,
                        help="Run only this phase number")
    parser.add_argument("--force", action="store_true",
                        help="Force re-run even if outputs exist")
    args = parser.parse_args()

    ensure_dirs()

    print(f"\n{'='*60}")
    print(f"HIVER SDE INTERN — AI SUPPORT AGENT PIPELINE")
    print(f"{'='*60}\n")

    # Check dataset
    if not (DATA_RAW / "twcs.csv").exists():
        print("ERROR: Dataset not found at data/raw/twcs.csv")
        print("Download from: https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter")
        print("Place twcs.csv in data/raw/")
        sys.exit(1)

    total_start = time.time()
    results = []

    for i, (name, module, check) in enumerate(PHASES, 1):
        if args.only is not None and i != args.only:
            continue
        if i < args.from_phase:
            print(f"  ⏭ Phase {i}: {name} — skipped")
            continue

        success = run_phase(name, module, check, force=args.force)
        results.append((name, success))

        if not success and args.only is None:
            print(f"\n⚠ Pipeline stopped at phase {i}. Fix the error and re-run with --from-phase {i}")
            break

    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"Pipeline completed in {total_elapsed:.1f}s")
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
