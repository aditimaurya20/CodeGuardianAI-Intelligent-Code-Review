import subprocess
import tempfile
import os
import re

def get_complexity_level(complexity):
    if complexity <= 5:
        return "Low"
    elif complexity <= 10:
        return "Moderate"
    elif complexity <= 20:
        return "High"
    else:
        return "Very High"

def run_radon_complexity(code, filename="uploaded_code.py"):
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as file:
            file.write(code)
            temp_file = file.name
        result = subprocess.run(
            ["radon", "cc", temp_file, "-s"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return {
                "success": False,
                "filename": filename,
                "average_complexity": None,
                "highest_complexity": None,
                "functions": [],
                "error": result.stderr.strip() or "Radon complexity analysis failed."
            }
        output = result.stdout.strip()
        functions = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            match = re.search(
                r"([A-Z])\s+(\d+):(\d+)\s+(.+?)\s+-\s+([A-Z])\s+\((\d+)\)",
                line
            )
            if match:
                grade = match.group(5)
                line_number = int(match.group(2))
                column = int(match.group(3))
                name = match.group(4).strip()
                complexity = int(match.group(6))
                functions.append({
                    "name": name,
                    "line": line_number,
                    "column": column,
                    "complexity": complexity,
                    "grade": grade,
                    "level": get_complexity_level(complexity)
                })
        if functions:
            complexity_values = [
                item["complexity"]
                for item in functions
            ]
            average_complexity = (
                sum(complexity_values) / len(complexity_values)
            )
            highest_complexity = max(complexity_values)
        else:
            average_complexity = 0
            highest_complexity = 0
        return {
            "success": True,
            "filename": filename,
            "average_complexity": round(average_complexity, 2),
            "highest_complexity": highest_complexity,
            "functions": functions
        }
    except FileNotFoundError:
        return {
            "success": False,
            "filename": filename,
            "average_complexity": None,
            "highest_complexity": None,
            "functions": [],
            "error": "Radon is not installed or could not be found."
        }
    except Exception as e:
        return {
            "success": False,
            "filename": filename,
            "average_complexity": None,
            "highest_complexity": None,
            "functions": [],
            "error": str(e)
        }
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

def run_radon_maintainability(code, filename="uploaded_code.py"):
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as file:
            file.write(code)
            temp_file = file.name
        result = subprocess.run(
            ["radon", "mi", temp_file, "-s"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return {
                "success": False,
                "filename": filename,
                "maintainability_index": None,
                "grade": None,
                "error": result.stderr.strip() or "Radon maintainability analysis failed."
            }
        output = result.stdout.strip()
        score = None
        grade = None
        match = re.search(
            r"-\s+([A-F])\s+\(([\d.]+)\)",
            output
        )
        if match:
            grade = match.group(1)
            score = float(match.group(2))
        if score is None:
            return {
                "success": False,
                "filename": filename,
                "maintainability_index": None,
                "grade": None,
                "error": "Radon did not return a maintainability score."
            }
        return {
            "success": True,
            "filename": filename,
            "maintainability_index": score,
            "grade": grade
        }
    except FileNotFoundError:
        return {
            "success": False,
            "filename": filename,
            "maintainability_index": None,
            "grade": None,
            "error": "Radon is not installed or could not be found."
        }
    except Exception as e:
        return {
            "success": False,
            "filename": filename,
            "maintainability_index": None,
            "grade": None,
            "error": str(e)
        }
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

def run_radon(code, filename="uploaded_code.py"):
    complexity = run_radon_complexity(code, filename)
    maintainability = run_radon_maintainability(code, filename)
    return {
        "complexity": complexity,
        "maintainability": maintainability
    }