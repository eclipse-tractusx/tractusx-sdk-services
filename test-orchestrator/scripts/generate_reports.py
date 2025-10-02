#!/usr/bin/env python
# *************************************************************
# Eclipse Tractus-X - Test Orchestrator Service
#
# Copyright (c) 2025 BMW AG
# Copyright (c) 2025 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
# *************************************************************

"""
Generate traceability reports in JSON and Markdown formats.

This script should be run after a successful test execution with coverage.
It parses coverage data and test results to generate comprehensive reports.
"""

import json
import os
import sys
import subprocess
import datetime
from pathlib import Path


def run_tests_with_coverage():
    """Run pytest with coverage and return the results."""
    print("Running tests with coverage...")
    
    # Change to the test-orchestrator directory
    os.chdir(Path(__file__).parent.parent)
    
    # Run pytest with coverage
    result = subprocess.run(
        ["pytest", "--cov=test_orchestrator", "--cov-report=term-missing"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("Tests failed! Report generation aborted.")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    
    return result.stdout


def extract_coverage_data(output):
    """Extract coverage data from pytest-cov output."""
    coverage_data = {}
    
    # Parse coverage percentage
    for line in output.split('\n'):
        if "TOTAL" in line:
            parts = line.split()
            if len(parts) >= 5:
                coverage_data["percentage"] = parts[3]
                break
    
    # Get missing lines information
    missing_lines = {}
    for line in output.split('\n'):
        if ".py" in line and "Missing" in line:
            file_path = line.split()[0]
            missing = line.split("Missing:")[1].strip()
            file_name = os.path.basename(file_path)
            missing_lines[file_name] = missing
    
    coverage_data["missing_lines"] = missing_lines
    return coverage_data


def generate_json_report(coverage_data):
    """Generate a JSON report with test and coverage data."""
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "coverage": {
            "percentage": coverage_data.get("percentage", "N/A"),
            "missing_lines": coverage_data.get("missing_lines", {})
        }
    }
    
    # Ensure the reports directory exists
    os.makedirs("reports", exist_ok=True)
    
    # Write JSON report
    with open("reports/traceability.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"JSON report generated: {os.path.abspath('reports/traceability.json')}")
    return report


def generate_markdown_report(report):
    """Generate a Markdown report from the JSON data."""
    timestamp = datetime.datetime.fromisoformat(report["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
    
    markdown = f"""# Traceability Test Report

Generated: {timestamp}

## Coverage Summary

- **Total Coverage**: {report['coverage']['percentage']}

## Missing Coverage Details

| File | Missing Lines |
|------|--------------|
"""
    
    # Add rows for each file with missing lines
    for file_name, missing in report['coverage']['missing_lines'].items():
        markdown += f"| {file_name} | {missing} |\n"
    
    # If no missing lines
    if not report['coverage']['missing_lines']:
        markdown += "| N/A | N/A |\n"
    
    # Write Markdown report
    with open("reports/traceability.md", "w") as f:
        f.write(markdown)
    
    print(f"Markdown report generated: {os.path.abspath('reports/traceability.md')}")


def main():
    """Main function to run tests and generate reports."""
    # Run tests and collect output
    test_output = run_tests_with_coverage()
    
    # Extract coverage data
    coverage_data = extract_coverage_data(test_output)
    
    # Generate reports
    json_report = generate_json_report(coverage_data)
    generate_markdown_report(json_report)
    
    print("Report generation complete.")


if __name__ == "__main__":
    main()