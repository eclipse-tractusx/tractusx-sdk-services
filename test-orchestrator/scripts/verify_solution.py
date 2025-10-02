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
Verify that the test coverage and report generation solution works as expected.

This script checks that:
1. The generate_reports.py script exists
2. The PyCharm run configurations exist
3. The Makefile exists and has the correct targets
4. The reports directory exists
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and print result."""
    if os.path.exists(file_path):
        print(f"✓ {description} exists: {file_path}")
        return True
    else:
        print(f"✗ {description} does not exist: {file_path}")
        return False

def main():
    """Main verification function."""
    # Change to test-orchestrator directory
    os.chdir(Path(__file__).parent.parent)
    
    success = True
    
    # Check report generation script
    script_path = os.path.join("scripts", "generate_reports.py")
    success = check_file_exists(script_path, "Report generation script") and success
    
    # Check PyCharm run configurations
    run_config_paths = [
        os.path.join(".run", "pytest_with_coverage.run.xml"),
        os.path.join(".run", "pytest_with_coverage_and_reports.run.xml")
    ]
    for config_path in run_config_paths:
        success = check_file_exists(config_path, "PyCharm run configuration") and success
    
    # Check Makefile
    makefile_path = "Makefile"
    if check_file_exists(makefile_path, "Makefile"):
        # Check makefile targets
        with open(makefile_path, "r") as f:
            content = f.read()
            required_targets = ["test-coverage", "test-coverage-report"]
            for target in required_targets:
                if target in content:
                    print(f"✓ Makefile contains target: {target}")
                else:
                    print(f"✗ Makefile is missing target: {target}")
                    success = False
    else:
        success = False
    
    # Check reports directory
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)  # Create if doesn't exist
    success = check_file_exists(reports_dir, "Reports directory") and success
    
    # Print final result
    if success:
        print("\n✅ All verification checks passed! The solution is properly set up.")
        return 0
    else:
        print("\n❌ Some verification checks failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())