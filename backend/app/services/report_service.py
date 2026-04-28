"""
Report Generation Service
==========================
Generates GRI-305 PDF reports and Excel exports.
Phase 2: extend with AI estimation summaries in the methodology appendix.
"""

import io
import pandas as pd
from datetime import date
from typing import List, Dict, Any


def generate_excel_report(records: List[Dict], summary: Dict) -> bytes:
    """
    Generate Excel report with multiple sheets:
    - Summary
    - Records (with full trace info)
    - Methodology
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Summary
        summary_data = {
            "Metric": [
                "Total Scope 3 Emissions (tCO2e)",
                "Total Records",
                "YoY Change (%)",
                "Report Generated",
                "Standard",
            ],
            "Value": [
                summary.get("total_co2e", 0),
                summary.get("record_count", 0),
                summary.get("yoy_change_pct", "N/A"),
                str(date.today()),
                "GHG Protocol Corporate Value Chain / GRI 305",
            ],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)

        # Sheet 2: Emission Records
        if records:
            records_df = pd.DataFrame(records)
            records_df.to_excel(writer, sheet_name="Emission Records", index=False)

        # Sheet 3: Methodology & EF Sources
        methodology = pd.DataFrame([
            {
                "Standard": "GHG Protocol",
                "Description": "Corporate Value Chain (Scope 3) Accounting and Reporting Standard",
                "URL": "https://ghgprotocol.org/scope-3-standard",
            },
            {
                "Standard": "GRI 305",
                "Description": "Emissions Disclosure Standard",
                "URL": "https://www.globalreporting.org/standards/media/1012/gri-305-emissions-2016.pdf",
            },
            {
                "Standard": "DEFRA",
                "Description": "UK Government Greenhouse Gas Conversion Factors",
                "URL": "https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
            },
            {
                "Standard": "IPCC AR6",
                "Description": "Sixth Assessment Report Emission Factors",
                "URL": "https://www.ipcc.ch/assessment-report/ar6/",
            },
        ])
        methodology.to_excel(writer, sheet_name="Methodology", index=False)

    return output.getvalue()


def generate_csv_template() -> bytes:
    """Download template for bulk upload."""
    df = pd.DataFrame(columns=[
        "category_id",
        "period_start",  # YYYY-MM-DD
        "period_end",    # YYYY-MM-DD
        "activity_value",
        "activity_unit",  # e.g. kg, km, INR, kWh
        "ef_id",
        "data_quality",   # A, B, or C
        "notes",
    ])
    # Add example row
    df.loc[0] = [1, "2024-04-01", "2024-06-30", 5000, "kg", 1, "B", "Sample entry"]
    return df.to_csv(index=False).encode()
