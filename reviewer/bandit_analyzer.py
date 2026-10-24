import json
import os
import subprocess
import sys
import tempfile


def run_bandit(code, filename="uploaded_code.py"):
    """
    Run Bandit security analysis on uploaded Python code.
    """

    temp_file = None

    try:

        # Create temporary Python file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as file:

            file.write(code)
            temp_file = file.name

        # Run Bandit
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "bandit",
                "-f",
                "json",
                "-q",
                temp_file
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout.strip()

        # Bandit can return a non-zero exit code
        # when security issues are found.
        # That is still a valid analysis result.

        if not output:

            return {
                "success": True,
                "filename": filename,
                "total_issues": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "issues": []
            }

        try:

            bandit_result = json.loads(output)

        except json.JSONDecodeError:

            return {
                "success": False,
                "filename": filename,
                "error": "Bandit returned invalid JSON output.",
                "details": result.stderr.strip(),
                "issues": [],
                "total_issues": 0
            }

        formatted_issues = []

        high = 0
        medium = 0
        low = 0

        for issue in bandit_result.get("results", []):

            severity = issue.get(
                "issue_severity",
                "LOW"
            ).upper()

            confidence = issue.get(
                "issue_confidence",
                "LOW"
            ).upper()

            if severity == "HIGH":
                high += 1

            elif severity == "MEDIUM":
                medium += 1

            else:
                low += 1

            formatted_issues.append({

                "type": "security",

                "code": issue.get(
                    "test_id",
                    ""
                ),

                "message": issue.get(
                    "issue_text",
                    ""
                ),

                "line": issue.get(
                    "line_number"
                ),

                "column": issue.get(
                    "col_offset"
                ),

                "severity": severity,

                "confidence": confidence,

                "path": filename
            })

        return {

            "success": True,

            "filename": filename,

            "total_issues":
                len(formatted_issues),

            "high":
                high,

            "medium":
                medium,

            "low":
                low,

            "issues":
                formatted_issues
        }

    except subprocess.TimeoutExpired:

        return {

            "success": False,

            "filename": filename,

            "error":
                "Bandit analysis timed out.",

            "issues": [],

            "total_issues": 0
        }

    except FileNotFoundError:

        return {

            "success": False,

            "filename": filename,

            "error":
                "Bandit is not installed or could not be found.",

            "issues": [],

            "total_issues": 0
        }

    except Exception as e:

        return {

            "success": False,

            "filename": filename,

            "error": str(e),

            "issues": [],

            "total_issues": 0
        }

    finally:

        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)