import os
import re
import shutil
import subprocess
import tempfile
from .analyzer import analyze_code

def detect_language(filename):
    extension = os.path.splitext(filename)[1].lower()
    language_map = {
        ".py": "Python",
        ".cpp": "C++",
        ".cc": "C++",
        ".cxx": "C++",
        ".h": "C++",
        ".hpp": "C++",
        ".java": "Java"
    }
    return language_map.get(extension, "Unknown")

def analyze_python(code, filename=None):
    result = analyze_code(code, "Python")
    result["language"] = "Python"
    result["success"] = True
    return result

def analyze_cpp(code, filename=None):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".cpp",
            delete=False,
            encoding="utf-8"
        ) as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name
        command = [
            "cppcheck",
            "--enable=all",
            "--inconclusive",
            "--template=gcc",
            temp_path
        ]
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = process.stdout + process.stderr
        issues = parse_cppcheck_output(output)
        return {
            "success": True,
            "language": "C++",
            "tool": "Cppcheck",
            "issues": issues,
            "total_issues": len(issues),
            "severity_summary": build_severity_summary(issues),
            "raw_output": output
        }
    except FileNotFoundError:
        return {
            "success": False,
            "language": "C++",
            "tool": "Cppcheck",
            "issues": [],
            "total_issues": 0,
            "severity_summary": build_severity_summary([]),
            "error": "Cppcheck is not installed."
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "language": "C++",
            "tool": "Cppcheck",
            "issues": [],
            "total_issues": 0,
            "severity_summary": build_severity_summary([]),
            "error": "Cppcheck analysis timed out."
        }
    except Exception as e:
        return {
            "success": False,
            "language": "C++",
            "tool": "Cppcheck",
            "issues": [],
            "total_issues": 0,
            "severity_summary": build_severity_summary([]),
            "error": str(e)
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

def parse_cppcheck_output(output):
    issues = []
    for line in output.splitlines():
        line = line.strip()
        if not line or "checkersReport" in line:
            continue
        match = re.match(
            r"(.+?):(\d+):(\d+):\s*(\w+):\s*(.+?)\s*\[(.+?)\]",
            line
        )
        if not match:
            continue
        file_path, line_number, column, severity, message, issue_code = match.groups()
        severity_lower = severity.lower()
        if severity_lower == "error":
            normalized_severity = "High"
        elif severity_lower in ["warning", "style", "performance", "portability"]:
            normalized_severity = "Medium"
        else:
            normalized_severity = "Low"
        issues.append({
            "tool": "Cppcheck",
            "file": file_path,
            "line": int(line_number),
            "column": int(column),
            "severity": normalized_severity,
            "type": severity,
            "code": issue_code,
            "message": message.strip()
        })
    return issues

def build_severity_summary(issues):
    summary = {
        "high": 0,
        "medium": 0,
        "low": 0,
        "total": len(issues)
    }
    for issue in issues:
        severity = issue.get("severity", "Low").lower()
        if severity == "high":
            summary["high"] += 1
        elif severity == "medium":
            summary["medium"] += 1
        else:
            summary["low"] += 1
    return summary

def parse_checkstyle_output(output):
    issues = []
    for line in output.splitlines():
        line = line.strip()
        if not line or ".java:" not in line:
            continue
        match = re.search(
            r"\.java:(\d+):(\d+):\s*(.*)",
            line
        )
        if not match:
            continue
        line_number = int(match.group(1))
        column = int(match.group(2))
        message = match.group(3).strip()
        issues.append({
            "tool": "Checkstyle",
            "line": line_number,
            "column": column,
            "severity": "Medium",
            "type": "Style",
            "code": "",
            "message": message
        })
    return issues

def parse_java_compiler_output(output):
    issues = []
    for line in output.splitlines():
        match = re.search(
            r"(.+?):(\d+):\s+error:\s+(.+)",
            line
        )
        if match:
            message = match.group(3)
            if "';' expected" in message:
                message = "Syntax error: invalid assignment operator. Use '=' instead of '=='."
            issues.append({
                "path": match.group(1),
                "line": int(match.group(2)),
                "column": 0,
                "code": "JAVAC",
                "message": message,
                "severity": "HIGH"
            })
    return issues

def analyze_java(code, filename=None):
    temp_path = None
    try:
        class_name = "CodeGuardianTemp"
        class_match = re.search(r"public\s+class\s+([A-Za-z_]\w*)", code)
        if class_match:
            class_name = class_match.group(1)
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, f"{class_name}.java")
        with open(temp_path, "w", encoding="utf-8") as temp_file:
            temp_file.write(code)
        checkstyle_path = os.path.join(
            os.path.dirname(__file__),
            "checkstyle.xml"
        )
        jar_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "tools",
            "checkstyle.jar"
        )
        if not os.path.exists(jar_path):
            return {
                "success": False,
                "language": "Java",
                "tool": "Checkstyle",
                "issues": [],
                "total_issues": 0,
                "severity_summary": build_severity_summary([]),
                "error": "Checkstyle JAR not found."
            }
        if not os.path.exists(checkstyle_path):
            return {
                "success": False,
                "language": "Java",
                "tool": "Checkstyle",
                "issues": [],
                "total_issues": 0,
                "severity_summary": build_severity_summary([]),
                "error": "Checkstyle configuration not found."
            }
        process = subprocess.run(
            [
                "java",
                "-jar",
                jar_path,
                "-c",
                checkstyle_path,
                temp_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = process.stdout + process.stderr
        issues = parse_checkstyle_output(output)
        compiler_process = subprocess.run(
            [
                "javac",
                temp_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        compiler_output = (
            compiler_process.stdout +
            compiler_process.stderr
        )
        compiler_issues = parse_java_compiler_output(
            compiler_output
        )
        issues.extend(compiler_issues)
        return {
            "success": True,
            "language": "Java",
            "tool": "Checkstyle + javac",
            "issues": issues,
            "total_issues": len(issues),
            "severity_summary": build_severity_summary(issues),
            "raw_output": output + compiler_output,
            "return_code": process.returncode
        }
    except FileNotFoundError:
        return {
            "success": False,
            "language": "Java",
            "tool": "Checkstyle + javac",
            "issues": [],
            "total_issues": 0,
            "severity_summary": build_severity_summary([]),
            "error": "Java is not installed or not available in PATH."
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "language": "Java",
            "tool": "Checkstyle + javac",
            "issues": [],
            "total_issues": 0,
            "severity_summary": build_severity_summary([]),
            "error": "Java analysis timed out."
        }
    except Exception as e:
        return {
            "success": False,
            "language": "Java",
            "tool": "Checkstyle + javac",
            "issues": [],
            "total_issues": 0,
            "severity_summary": build_severity_summary([]),
            "error": str(e)
        }
    finally:
        if temp_path:
            temp_dir = os.path.dirname(temp_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

def analyze_by_language(code, language, filename=None):
    if language == "Python":
        return analyze_python(code, filename)
    if language == "C++":
        return analyze_cpp(code, filename)
    if language == "Java":
        return analyze_java(code, filename)
    return {
        "success": False,
        "language": language or "Unknown",
        "issues": [],
        "total_issues": 0,
        "severity_summary": build_severity_summary([]),
        "error": "Unsupported programming language."
    }