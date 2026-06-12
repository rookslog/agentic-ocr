"""Generate evaluation reports in various formats.

This module provides:
1. generate_cli_report() - Terminal-friendly table output
2. generate_json_report() - Machine-readable JSON
3. generate_html_report() - Visual HTML report
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from tabulate import tabulate

from eval.lib.metrics import AggregateMetrics


def generate_cli_report(
    metrics: AggregateMetrics,
    title: str = "Ground Truth Evaluation Report",
    baseline: AggregateMetrics | None = None,
) -> str:
    """Generate a CLI-friendly report with tables.

    Args:
        metrics: Aggregate metrics to report
        title: Report title
        baseline: Optional baseline metrics for comparison

    Returns:
        Formatted string for terminal output
    """
    lines = []
    lines.append("=" * 60)
    lines.append(title)
    lines.append("=" * 60)
    lines.append("")

    # Summary stats
    total_gt = sum(m.support for m in metrics.by_type.values())
    total_pred = sum(m.true_positives + m.false_positives for m in metrics.by_type.values())
    lines.append(f"Ground Truth Elements: {total_gt}")
    lines.append(f"Predicted Elements: {total_pred}")
    lines.append("")

    # Per-type table
    headers = ["Element Type", "Precision", "Recall", "F1", "Support"]
    if baseline:
        headers.append("F1 Delta")

    rows = []
    for element_type, m in sorted(metrics.by_type.items()):
        row = [
            element_type,
            f"{m.precision:.3f}",
            f"{m.recall:.3f}",
            f"{m.f1:.3f}",
            str(m.support),
        ]

        if baseline and element_type in baseline.by_type:
            base_f1 = baseline.by_type[element_type].f1
            delta = m.f1 - base_f1
            delta_str = f"{delta:+.3f}" if delta != 0 else "0.000"
            row.append(delta_str)

        rows.append(row)

    lines.append(tabulate(rows, headers=headers, tablefmt="simple"))
    lines.append("")

    # Aggregate metrics
    lines.append("-" * 40)
    lines.append(f"Micro F1: {metrics.micro_f1:.4f}")
    lines.append(f"Macro F1: {metrics.macro_f1:.4f}")

    if baseline:
        micro_delta = metrics.micro_f1 - baseline.micro_f1
        lines.append(f"Micro F1 Delta: {micro_delta:+.4f}")

    lines.append("")

    # Error summary (if any)
    all_errors: dict[str, int] = {}
    for m in metrics.by_type.values():
        for err_type, count in m.error_counts.items():
            all_errors[err_type] = all_errors.get(err_type, 0) + count

    if all_errors:
        lines.append("Error Summary:")
        for err_type, count in sorted(all_errors.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  {err_type}: {count}")

    lines.append("")
    return "\n".join(lines)


def generate_json_report(
    metrics: AggregateMetrics,
    pdf_path: str | None = None,
    ground_truth_path: str | None = None,
    extraction_config: dict | None = None,
) -> dict[str, Any]:
    """Generate a JSON-serializable report.

    Args:
        metrics: Aggregate metrics
        pdf_path: Optional path to source PDF
        ground_truth_path: Optional path to ground truth YAML
        extraction_config: Optional extraction configuration used

    Returns:
        Dictionary suitable for JSON serialization
    """
    return {
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "source": {
            "pdf": pdf_path,
            "ground_truth": ground_truth_path,
        },
        "extraction_config": extraction_config,
        "aggregate_metrics": metrics.to_dict(),
    }


def save_json_report(
    metrics: AggregateMetrics,
    output_path: Path,
    pdf_path: str | None = None,
    ground_truth_path: str | None = None,
    extraction_config: dict | None = None,
) -> None:
    """Save JSON report to file.

    Args:
        metrics: Aggregate metrics
        output_path: Path to write JSON file
        pdf_path: Optional path to source PDF
        ground_truth_path: Optional path to ground truth YAML
        extraction_config: Optional extraction configuration
    """
    report = generate_json_report(
        metrics,
        pdf_path=pdf_path,
        ground_truth_path=ground_truth_path,
        extraction_config=extraction_config,
    )
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)


def _render_error_section(error_rows: str) -> str:
    """Render error analysis section for HTML report."""
    if not error_rows:
        return ""
    return (
        "<div class='card'><h2>Error Analysis</h2>"
        "<table><thead><tr><th>Error Type</th><th>Count</th></tr></thead>"
        f"<tbody>{error_rows}</tbody></table></div>"
    )


def generate_html_report(
    metrics: AggregateMetrics,
    output_path: Path,
    title: str = "Ground Truth Evaluation Report",
    pdf_path: str | None = None,
    ground_truth_path: str | None = None,
) -> None:
    """Generate an HTML report with visualizations.

    Args:
        metrics: Aggregate metrics
        output_path: Path to write HTML file
        title: Report title
        pdf_path: Optional source PDF path
        ground_truth_path: Optional ground truth YAML path
    """
    # Build per-type rows
    type_rows = ""
    for element_type, m in sorted(metrics.by_type.items()):
        # Determine status color
        if m.f1 >= 0.9:
            status_class = "status-good"
        elif m.f1 >= 0.7:
            status_class = "status-ok"
        else:
            status_class = "status-bad"

        type_rows += f"""
        <tr>
            <td>{element_type}</td>
            <td>{m.true_positives}</td>
            <td>{m.false_positives}</td>
            <td>{m.false_negatives}</td>
            <td>{m.precision:.3f}</td>
            <td>{m.recall:.3f}</td>
            <td class="{status_class}">{m.f1:.3f}</td>
            <td>{m.support}</td>
        </tr>
        """

    # Error summary
    all_errors: dict[str, int] = {}
    for m in metrics.by_type.values():
        for err_type, count in m.error_counts.items():
            all_errors[err_type] = all_errors.get(err_type, 0) + count

    error_rows = ""
    for err_type, count in sorted(all_errors.items(), key=lambda x: -x[1])[:10]:
        error_rows += f"<tr><td>{err_type}</td><td>{count}</td></tr>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .card {{
                background: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1, h2, h3 {{
                margin-top: 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }}
            th {{
                background: #f8f9fa;
                font-weight: 600;
            }}
            .metric-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
            }}
            .metric-box {{
                text-align: center;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
            }}
            .metric-value {{
                font-size: 2em;
                font-weight: bold;
                color: #333;
            }}
            .metric-label {{
                color: #666;
                margin-top: 5px;
            }}
            .status-good {{ color: #28a745; font-weight: bold; }}
            .status-ok {{ color: #ffc107; font-weight: bold; }}
            .status-bad {{ color: #dc3545; font-weight: bold; }}
            .meta {{
                color: #666;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>{title}</h1>
                <p class="meta">
                    Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
                    PDF: {pdf_path or "N/A"}<br>
                    Ground Truth: {ground_truth_path or "N/A"}
                </p>
            </div>

            <div class="card">
                <h2>Summary Metrics</h2>
                <div class="metric-grid">
                    <div class="metric-box">
                        <div class="metric-value">{metrics.micro_f1:.3f}</div>
                        <div class="metric-label">Micro F1</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{metrics.micro_precision:.3f}</div>
                        <div class="metric-label">Micro Precision</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-value">{metrics.micro_recall:.3f}</div>
                        <div class="metric-label">Micro Recall</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Per-Type Metrics</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Element Type</th>
                            <th>TP</th>
                            <th>FP</th>
                            <th>FN</th>
                            <th>Precision</th>
                            <th>Recall</th>
                            <th>F1</th>
                            <th>Support</th>
                        </tr>
                    </thead>
                    <tbody>
                        {type_rows}
                    </tbody>
                </table>
            </div>

            {_render_error_section(error_rows)}
        </div>
    </body>
    </html>
    """

    with open(output_path, "w") as f:
        f.write(html)
