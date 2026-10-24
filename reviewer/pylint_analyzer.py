import json
import os
import subprocess
import sys
import tempfile


def run_pylint(code, filename="uploaded_code.py"):
    """
    Run Pylint on uploaded Python code
    and return structured analysis results.
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

        # Run Pylint using the same Python environment
        # that is running Django.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pylint",
                temp_file,
                "--output-format=json",
                "--reports=no"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Pylint returns non-zero when issues are found.
        # That is normal and is NOT an execution failure.

        if not result.stdout.strip():

            return {
                "success": False,
                "filename": filename,
                "error": "Pylint execution failed.",
                "details": result.stderr.strip()
            }

        try:
            issues = json.loads(result.stdout)

        except json.JSONDecodeError:

            return {
                "success": False,
                "filename": filename,
                "error": "Pylint returned invalid JSON output.",
                "details": result.stderr.strip()
            }
        formatted_issues = []

        for issue in issues:

            formatted_issues.append({
                "type": issue.get("type", "unknown"),
                "message": issue.get("message", ""),
                "symbol": issue.get("symbol", ""),
                "message_id": issue.get("message-id", ""),
                "line": issue.get("line"),
                "column": issue.get("column"),
                "path": filename
            })

        # Count issue types
        errors = 0
        warnings = 0
        conventions = 0
        refactors = 0

        for issue in formatted_issues:

            issue_type = issue["type"]

            if issue_type == "error":
                errors += 1

            elif issue_type == "warning":
                warnings += 1

            elif issue_type == "convention":
                conventions += 1

            elif issue_type == "refactor":
                refactors += 1

        return {
            "success": True,
            "filename": filename,
            "total_issues": len(formatted_issues),
            "errors": errors,
            "warnings": warnings,
            "conventions": conventions,
            "refactors": refactors,
            "issues": formatted_issues
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "error": "Pylint analysis timed out."
        }

    except FileNotFoundError:

        return {
            "success": False,
            "error": "Pylint is not installed or could not be found."
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }

    finally:

        # Delete temporary file
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)