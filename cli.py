"""
Command-Line Interface (CLI) for MoodMeter.
Allows direct terminal analysis of individual reviews or batch CSV files.
"""

import argparse
import csv
import json
import sys
from triage_engine import process_review


def main():
    parser = argparse.ArgumentParser(description="MoodMeter: Analyze customer review sentiment and triage routing.")
    parser.add_argument("text", nargs="?", default=None, help="Review text to analyze directly.")
    parser.add_argument("--product", default="General Product", help="Product name.")
    parser.add_argument("--file", default=None, help="Path to CSV file with reviews to process in batch.")
    args = parser.parse_args()

    if args.file:
        print(f"Reading reviews from {args.file}...")
        with open(args.file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            urgent = 0
            for row in reader:
                count += 1
                res = process_review(row.get("text", ""), row.get("product", "Unknown"), review_id=f"BATCH-{count:03d}")
                flag = "[URGENT]" if res["urgency"]["is_urgent"] else "[NORMAL]"
                if res["urgency"]["is_urgent"]:
                    urgent += 1
                print(f"{flag} {res['product']} | {res['sentiment']['label']} ({res['sentiment']['polarity']:+.2f}) -> {res['suggested_team']}")
            print(f"\nProcessed {count} reviews ({urgent} urgent cases).")
        return

    if not args.text:
        parser.print_help()
        sys.exit(1)

    result = process_review(args.text, args.product)
    print("\n=== MoodMeter Analysis ===")
    print(f"Product   : {result['product']}")
    print(f"Sentiment : {result['sentiment']['label']} (Polarity: {result['sentiment']['polarity']:+.2f})")
    print(f"Themes    : {', '.join(result['themes'])}")
    print(f"Priority  : {'URGENT (P1)' if result['urgency']['is_urgent'] else 'Normal (P2)'}")
    print(f"Routing   : {result['suggested_team']}")
    print(f"Action    : {result['triage_explanation']}\n")


if __name__ == "__main__":
    main()
