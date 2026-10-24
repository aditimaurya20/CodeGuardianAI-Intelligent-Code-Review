import os
import re
import subprocess
import sys
import tempfile


def run_flake8(code, filename="uploaded_code.py"):
    """
    Run Flake8 on uploaded Python code
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

        # Run Flake8
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "flake8",
                temp_file
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout.strip()

        formatted_issues = []

        # Example Flake8 output:
        #
        # /tmp/test.py:1:1: F401 'os' imported but unused
        #
        pattern = re.compile(
            r"^.*?:(\d+):(\d+):\s+"
            r"([A-Z]\d+)\s+(.*)$"
        )

        for line in output.splitlines():

            match = pattern.match(line.strip())

            if not match:
                continue

            line_number = int(match.group(1))
            column_number = int(match.group(2))
            error_code = match.group(3)
            message = match.group(4)

            formatted_issues.append({
                "type": "style",
                "code": error_code,
                "message": message,
                "line": line_number,
                "column": column_number,
                "path": filename
            })

        return {
            "success": True,
            "filename": filename,
            "total_issues": len(formatted_issues),
            "issues": formatted_issues
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "filename": filename,
            "error": "Flake8 analysis timed out.",
            "issues": [],
            "total_issues": 0
        }

    except FileNotFoundError:

        return {
            "success": False,
            "filename": filename,
            "error": "Flake8 is not installed or could not be found.",
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