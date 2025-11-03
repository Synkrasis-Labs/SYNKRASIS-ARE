#!/usr/bin/env python3
"""
Script to run evaluations for multiple scenarios and generate reports.

This script:
1. Runs evaluations for a configurable list of scenarios
2. Parses the JSON results to generate CSV and summary reports
3. Provides comprehensive analysis of evaluation metrics
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def load_scenario_config(config_path: str) -> dict[str, Any]:
    """Load scenario configuration from YAML file."""
    with open(config_path, "r") as f:
        if config_path.endswith(".yaml") or config_path.endswith(".yml"):
            return yaml.safe_load(f)
        else:
            return json.load(f)


def run_scenario_evaluation(
    scenario_name: str,
    model: str,
    provider: str,
    agent: str = "default",
    endpoint: str | None = None,
    results_dir: str = "evaluation_results",
) -> bool:
    """Run evaluation for a single scenario."""
    print(f"🚀 Running evaluation for scenario: {scenario_name}")

    cmd = [
        "are-run",
        "-s",
        scenario_name,
        "-a",
        agent,
        "--model",
        model,
        "--provider",
        provider,
    ]

    # Optionally pass a custom endpoint to are-run
    if endpoint:
        cmd.extend(["--endpoint", endpoint])

    # Set up environment to pass scenario name and results directory to the core scenario
    env = os.environ.copy()
    env["SCENARIO_NAME"] = scenario_name
    env["EVALUATION_RESULTS_DIR"] = results_dir

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, env=env
        )  # 10 minute timeout
        if result.returncode == 0:
            print(f"✅ Successfully completed scenario: {scenario_name}")
            return True
        else:
            print(f"❌ Failed to run scenario: {scenario_name}")
            print(f"Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout running scenario: {scenario_name}")
        return False
    except Exception as e:
        print(f"💥 Exception running scenario {scenario_name}: {e}")
        return False


def collect_json_results(
    results_dir: str = "evaluation_results",
) -> list[dict[str, Any]]:
    """Collect all JSON result files from the results directory."""
    results = []
    results_path = Path(results_dir)

    if not results_path.exists():
        print(f"⚠️  Results directory {results_dir} does not exist")
        return results

    json_files = list(results_path.glob("*.json"))
    print(f"📂 Found {len(json_files)} JSON result files")

    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                data["source_file"] = str(json_file)
                results.append(data)
        except Exception as e:
            print(f"⚠️  Error loading {json_file}: {e}")

    return results


def generate_csv_report(results: list[dict[str, Any]], output_path: str):
    """Generate CSV report from evaluation results."""
    if not results:
        print("⚠️  No results to generate CSV report")
        return

    print(f"📊 Generating CSV report: {output_path}")

    # Prepare CSV data
    csv_data = []

    for result in results:
        scenario_name = result.get("scenario_name", "Unknown")
        timestamp = result.get("timestamp", "")
        summary = result.get("summary", {})

        # Base row data
        base_row = {
            "scenario_name": scenario_name,
            "timestamp": timestamp,
            "total_sequences": summary.get("total_sequences", 0),
            "avg_harmful_rate": summary.get("avg_harmful_rate", 0),
            "avg_efficiency": summary.get("avg_efficiency", None),
            "avg_prefix_criticality": summary.get("avg_prefix_criticality", None),
        }

        # Add distance algorithm averages
        for key, value in summary.items():
            if key.startswith("avg_") and key.endswith("_distance"):
                base_row[key] = value

        # Add per-sequence data
        sequences = result.get("sequences", [])
        if sequences:
            for seq_data in sequences:
                row = base_row.copy()
                row.update(
                    {
                        "sequence_index": seq_data.get("sequence_index", 0),
                        "sequence_harmful_rate": seq_data.get("harmful_rate", 0),
                        "sequence_prefix_criticality": seq_data.get(
                            "prefix_criticality", None
                        ),
                        "sequence_efficiency": seq_data.get("efficiency", None),
                    }
                )

                # Add distance metrics
                distance_metrics = seq_data.get("distance_metrics", {})
                for algo_name, metrics in distance_metrics.items():
                    row[f"sequence_{algo_name}_distance"] = metrics.get(
                        "best_distance", 0
                    )

                csv_data.append(row)
        else:
            csv_data.append(base_row)

    # Write CSV
    if csv_data:
        fieldnames = set()
        for row in csv_data:
            fieldnames.update(row.keys())
        fieldnames = sorted(fieldnames)

        with open(output_path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)

        print(f"✅ CSV report saved to: {output_path}")


def generate_summary_report(results: list[dict[str, Any]], output_path: str):
    """Generate summary text report from evaluation results."""
    if not results:
        print("⚠️  No results to generate summary report")
        return

    print(f"📋 Generating summary report: {output_path}")

    with open(output_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("CORE SCENARIO EVALUATION SUMMARY REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Scenarios Evaluated: {len(results)}\n\n")

        # Overall statistics
        f.write("OVERALL STATISTICS\n")
        f.write("-" * 40 + "\n")

        total_sequences = sum(
            r.get("summary", {}).get("total_sequences", 0) for r in results
        )
        f.write(f"Total Sequences Across All Scenarios: {total_sequences}\n")

        # Calculate averages across all scenarios
        harmful_rates = [
            r.get("summary", {}).get("avg_harmful_rate", 0)
            for r in results
            if r.get("summary", {}).get("avg_harmful_rate") is not None
        ]
        if harmful_rates:
            f.write(
                f"Average Harmful Rate: {sum(harmful_rates) / len(harmful_rates):.4f}\n"
            )

        efficiencies = [
            r.get("summary", {}).get("avg_efficiency")
            for r in results
            if r.get("summary", {}).get("avg_efficiency") is not None
        ]
        if efficiencies:
            f.write(
                f"Average Efficiency: {sum(efficiencies) / len(efficiencies):.4f}\n"
            )

        prefix_criticalities = [
            r.get("summary", {}).get("avg_prefix_criticality")
            for r in results
            if r.get("summary", {}).get("avg_prefix_criticality") is not None
        ]
        if prefix_criticalities:
            f.write(
                f"Average Prefix Criticality: {sum(prefix_criticalities) / len(prefix_criticalities):.4f}\n"
            )

        # Distance algorithm performance
        distance_algos = set()
        for result in results:
            for key in result.get("summary", {}).keys():
                if key.startswith("avg_") and key.endswith("_distance"):
                    distance_algos.add(key)

        if distance_algos:
            f.write("\nDISTANCE ALGORITHM PERFORMANCE\n")
            f.write("-" * 40 + "\n")
            for algo in sorted(distance_algos):
                values = [
                    r.get("summary", {}).get(algo, 0)
                    for r in results
                    if r.get("summary", {}).get(algo) is not None
                ]
                if values:
                    f.write(f"{algo}: {sum(values) / len(values):.4f}\n")

        # Per-scenario breakdown
        f.write("\nPER-SCENARIO BREAKDOWN\n")
        f.write("-" * 40 + "\n")

        for i, result in enumerate(results, 1):
            scenario_name = result.get("scenario_name", f"Scenario_{i}")
            summary = result.get("summary", {})

            f.write(f"\n{i}. {scenario_name}\n")
            f.write(f"   Timestamp: {result.get('timestamp', 'Unknown')}\n")
            f.write(f"   Sequences: {summary.get('total_sequences', 0)}\n")
            f.write(f"   Harmful Rate: {summary.get('avg_harmful_rate', 0):.4f}\n")

            if summary.get("avg_efficiency") is not None:
                f.write(f"   Efficiency: {summary.get('avg_efficiency'):.4f}\n")
            else:
                f.write("   Efficiency: N/A\n")

            if summary.get("avg_prefix_criticality") is not None:
                f.write(
                    f"   Prefix Criticality: {summary.get('avg_prefix_criticality'):.4f}\n"
                )
            else:
                f.write("   Prefix Criticality: N/A\n")

            # Distance metrics
            for key, value in summary.items():
                if key.startswith("avg_") and key.endswith("_distance"):
                    algo_name = key.replace("avg_", "").replace("_distance", "")
                    f.write(f"   {algo_name} Distance: {value:.4f}\n")

            # Add per-sequence symbol sequences
            sequences = result.get("sequences", [])
            if sequences:
                f.write("\n   Per-Sequence Details:\n")
                agent_symbols = result.get("agent_symbol_sequence", [])
                f.write(f"   Agent Symbol Sequence: {agent_symbols}\n")

                for seq_data in sequences:
                    seq_idx = seq_data.get("sequence_index", 0)
                    expected_symbols = seq_data.get("expected_symbol_sequence", [])
                    f.write(
                        f"   Sequence {seq_idx} Expected Symbols: {expected_symbols}\n"
                    )

                    # Add key metrics for this sequence
                    harmful_rate = seq_data.get("harmful_rate", 0)
                    prefix_crit = seq_data.get("prefix_criticality")
                    efficiency = seq_data.get("efficiency")

                    f.write(f"   Sequence {seq_idx} Metrics: ")
                    f.write(f"Harmful Rate={harmful_rate:.4f}, ")
                    prefix_crit_str = (
                        f"{prefix_crit:.4f}" if prefix_crit is not None else "N/A"
                    )
                    efficiency_str = (
                        f"{efficiency:.4f}" if efficiency is not None else "N/A"
                    )
                    f.write(f"Prefix Criticality={prefix_crit_str}, ")
                    f.write(f"Efficiency={efficiency_str}\n")

                    # Add distance metrics for this sequence
                    distance_metrics = seq_data.get("distance_metrics", {})
                    if distance_metrics:
                        f.write(f"   Sequence {seq_idx} Distances: ")
                        for algo_name, metrics in distance_metrics.items():
                            best_distance = metrics.get("best_distance", 0)
                            f.write(f"{algo_name}={best_distance:.4f} ")
                        f.write("\n")
                f.write("\n")

        # Performance insights
        f.write("\nPERFORMANCE INSIGHTS\n")
        f.write("-" * 40 + "\n")

        if harmful_rates:
            best_scenario_idx = harmful_rates.index(min(harmful_rates))
            worst_scenario_idx = harmful_rates.index(max(harmful_rates))
            f.write(
                f"Lowest Harmful Rate: {results[best_scenario_idx].get('scenario_name')} ({min(harmful_rates):.4f})\n"
            )
            f.write(
                f"Highest Harmful Rate: {results[worst_scenario_idx].get('scenario_name')} ({max(harmful_rates):.4f})\n"
            )

        if efficiencies:
            best_eff_idx = efficiencies.index(max(efficiencies))
            f.write(
                f"Best Efficiency: {[r for r in results if r.get('summary', {}).get('avg_efficiency') is not None][best_eff_idx].get('scenario_name')} ({max(efficiencies):.4f})\n"
            )

        f.write("\n" + "=" * 80 + "\n")

    print(f"✅ Summary report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run CORE scenario evaluations and generate reports"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to scenario configuration file (YAML or JSON)",
    )
    parser.add_argument(
        "--model", "-m", help="Model to use for evaluation (overrides config)"
    )
    parser.add_argument("--provider", "-p", help="Model provider (overrides config)")
    parser.add_argument(
        "--agent", "-a", help="Agent to use (overrides config, default: default)"
    )
    parser.add_argument(
        "--endpoint",
        help="Custom API endpoint/base URL for the model provider (overrides config)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="evaluation_reports",
        help="Output directory for reports",
    )
    parser.add_argument(
        "--results-dir",
        "-r",
        default="evaluation_results",
        help="Directory containing JSON results",
    )
    parser.add_argument(
        "--skip-evaluation",
        action="store_true",
        help="Skip running evaluations, only generate reports",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_scenario_config(args.config)
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)

    # Get model/provider from config defaults if not provided via command line
    default_model_config = config.get("default_model", {})
    model = args.model or default_model_config.get("name")
    provider = args.provider or default_model_config.get("provider")
    endpoint = args.endpoint or default_model_config.get("endpoint")
    agent = args.agent or default_model_config.get("agent", "default")

    # Validate that we have required parameters
    if not model:
        print(
            "❌ No model specified. Provide --model or set default_model.name in config"
        )
        sys.exit(1)

    if not provider:
        print(
            "❌ No provider specified. Provide --provider or set default_model.provider in config"
        )
        sys.exit(1)

    scenarios = config.get("scenarios", [])
    if not scenarios:
        print("❌ No scenarios found in configuration")
        sys.exit(1)

    print(f"📋 Loaded {len(scenarios)} scenarios from configuration")
    ep_str = f", endpoint: {endpoint}" if endpoint else ""
    print(f"🔧 Using model: {model} (provider: {provider}{ep_str}, agent: {agent})")

    # Create timestamped directory for this evaluation run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_results_dir = os.path.join(args.results_dir, f"run_{timestamp}")
    run_reports_dir = os.path.join(args.output_dir, f"run_{timestamp}")

    # Run evaluations if not skipped
    if not args.skip_evaluation:
        ep_str = f", endpoint: {endpoint}" if endpoint else ""
        print(f"\n🚀 Starting evaluations with model: {model} (provider: {provider}{ep_str})")
        print(f"📁 Results will be saved to: {run_results_dir}")

        successful_runs = 0
        failed_runs = 0

        for scenario in scenarios:
            success = run_scenario_evaluation(
                scenario, model, provider, agent, endpoint, run_results_dir
            )
            if success:
                successful_runs += 1
            else:
                failed_runs += 1

        print("\n📊 Evaluation Summary:")
        print(f"   ✅ Successful: {successful_runs}")
        print(f"   ❌ Failed: {failed_runs}")

        # Generate reports from this run's results
        print(f"\n📋 Generating reports from {run_results_dir}")
        results = collect_json_results(run_results_dir)

        if not results:
            print("❌ No results found to generate reports")
            sys.exit(1)

        # Create output directory for this run
        os.makedirs(run_reports_dir, exist_ok=True)

        # Generate CSV report
        csv_path = os.path.join(run_reports_dir, f"evaluation_metrics_{timestamp}.csv")
        generate_csv_report(results, csv_path)

        # Generate summary report
        summary_path = os.path.join(
            run_reports_dir, f"evaluation_summary_{timestamp}.txt"
        )
        generate_summary_report(results, summary_path)

        print("\n🎉 Reports generated successfully!")
        print(f"   📊 CSV Report: {csv_path}")
        print(f"   📋 Summary Report: {summary_path}")

    else:
        # Skip evaluation mode - use provided results directory
        print(f"\n📋 Generating reports from {args.results_dir}")
        results = collect_json_results(args.results_dir)

        if not results:
            print("❌ No results found to generate reports")
            sys.exit(1)

        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)

        # Generate CSV report
        csv_path = os.path.join(args.output_dir, f"evaluation_metrics_{timestamp}.csv")
        generate_csv_report(results, csv_path)

        # Generate summary report
        summary_path = os.path.join(
            args.output_dir, f"evaluation_summary_{timestamp}.txt"
        )
        generate_summary_report(results, summary_path)

        print("\n🎉 Reports generated successfully!")
        print(f"   📊 CSV Report: {csv_path}")
        print(f"   📋 Summary Report: {summary_path}")


if __name__ == "__main__":
    main()
