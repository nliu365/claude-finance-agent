#!/usr/bin/env python3
"""
Batch analysis of multiple 10-K files
"""

import asyncio
import os
import json
from pathlib import Path
from finance_analyzer import FinanceCoordinator


async def analyze_batch(data_dir: str, output_dir: str, limit: int = None):
    """
    Batch analyze all 10-K JSON files in the specified directory

    Args:
        data_dir: Directory containing 10-K JSON files
        output_dir: Directory to save analysis results
        limit: Limit the number of files to analyze
    """
    print("=" * 80)
    print("🔄 BATCH FINANCE ANALYSIS")
    print("   Using Claude Agent SDK with default settings")
    print("=" * 80)

    # Find all JSON files
    json_files = list(Path(data_dir).glob("*.json"))

    if limit:
        json_files = json_files[:limit]

    print(f"\n📂 Found {len(json_files)} files to analyze")
    print(f"💾 Results will be saved to: {output_dir}\n")

    os.makedirs(output_dir, exist_ok=True)

    coordinator = FinanceCoordinator()

    results_summary = []

    for i, file_path in enumerate(json_files, 1):
        print(f"\n{'=' * 80}")
        print(f"📊 Analyzing file {i}/{len(json_files)}: {file_path.name}")
        print(f"{'=' * 80}")

        try:
            report = await coordinator.analyze_company(str(file_path), output_dir=output_dir)
            coordinator.print_report(report)

            # Add to summary
            results_summary.append({
                "file": file_path.name,
                "cik": file_path.stem.split('_')[0],
                "overall_score": report['scores']['overall_score'],
                "grade": report['scores']['grade'],
                "recommendation": report['recommendation']['rating'],
                "risk_level": report['recommendation']['risk_level'],
            })

        except Exception as e:
            print(f"\n❌ Error analyzing {file_path.name}: {e}")
            results_summary.append({
                "file": file_path.name,
                "error": str(e)
            })

    # Save batch analysis summary
    summary_path = os.path.join(output_dir, "batch_summary.json")
    with open(summary_path, 'w') as f:
        json.dump({
            "total_files": len(json_files),
            "results": results_summary
        }, f, indent=2)

    print(f"\n\n{'=' * 80}")
    print("✅ BATCH ANALYSIS COMPLETE")
    print(f"{'=' * 80}")
    print(f"📊 Analyzed: {len(json_files)} files")
    print(f"💾 Summary saved: {summary_path}")

    # Print quick summary
    print(f"\n📈 Quick Summary:")
    print("-" * 80)
    for item in results_summary:
        if 'error' not in item:
            print(f"  {item['file']:30} | {item['grade']:20} | {item['recommendation']:15} | {item['risk_level']}")
        else:
            print(f"  {item['file']:30} | ERROR: {item['error']}")


async def main():
    """Batch analysis example"""
    import sys

    # Default parameters (relative to project root)
    data_dir = "data/10k_2020_10_critical_sections"
    output_dir = "data/results"
    limit = None

    # Command line arguments
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    if len(sys.argv) > 3:
        limit = int(sys.argv[3])

    await analyze_batch(data_dir, output_dir, limit)


if __name__ == "__main__":
    asyncio.run(main())
