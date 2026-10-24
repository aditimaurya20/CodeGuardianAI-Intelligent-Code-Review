SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"
SEVERITY_LOW = "Low"


def classify_severity(
    tool,
    issue_code=None,
    message=""
):
    """
    Classify a static-analysis issue
    as High, Medium, or Low severity.
    """

    tool = tool.lower()
    message_lower = message.lower()

    if tool == "bandit":
        high_codes = [
            "B602",
            "B603",
            "B604",
            "B605",
            "B606"
        ]
        medium_codes = [
            "B301",
            "B303",
            "B324",
            "B501",
            "B506"
        ]
        code = (issue_code or "").upper()
        if code in high_codes:
            return SEVERITY_HIGH
        if code in medium_codes:
            return SEVERITY_MEDIUM
        high_keywords = [
            "command injection",
            "sql injection",
            "remote code execution",
            "shell injection"
        ]
        medium_keywords = [
            "weak cryptography",
            "md5",
            "sha1",
            "hardcoded password"
        ]
        for keyword in high_keywords:
            if keyword in message_lower:
                return SEVERITY_HIGH
        for keyword in medium_keywords:
            if keyword in message_lower:
                return SEVERITY_MEDIUM
        return SEVERITY_LOW

    if tool == "pylint":
        if issue_code:
            if issue_code.startswith("E"):
                return SEVERITY_HIGH

            if issue_code.startswith("W"):
                return SEVERITY_MEDIUM

            if issue_code.startswith("C"):
                return SEVERITY_LOW

        return SEVERITY_LOW

    if tool == "flake8":
        if issue_code:
            formatting_codes = [
                "E101","E111","E114","E115","E116","E117","E121","E122","E123","E124","E125","E126","E127","E128","E129","E131",
                "E201","E202","E203","E211","E221","E222","E223","E224","E225","E226","E227","E228","E231","E241","E242","E251",
                "E261","E262","E265","E266","E271","E272","E273","E274","E275",
                "E301",
                "E302",
                "E303",
                "E304",
                "E305",
                "E306",
                "E307",
                "E308"
            ]
            code = issue_code.upper()
            if code in formatting_codes:
                return SEVERITY_LOW
            if code.startswith("F"):
                return SEVERITY_HIGH
            if code.startswith("E"):
                return SEVERITY_MEDIUM
            if code.startswith("W"):
                return SEVERITY_LOW
        return SEVERITY_LOW

    return SEVERITY_LOW


def create_issue(
    tool,
    line,
    issue_type,
    message,
    issue_code=None
):
    severity = classify_severity(
        tool,
        issue_code,
        message
    )

    return {
        "tool": tool,
        "line": line,
        "type": issue_type,
        "code": issue_code,
        "severity": severity,
        "message": message
    }


def collect_all_issues(static_results):
    issues = []

    pylint = static_results.get("pylint")

    if pylint:
        for issue in pylint.get("issues", []):
            issues.append(
                create_issue(
                    tool="Pylint",
                    line=issue.get("line"),
                    issue_type="Code Quality",
                    message=issue.get("message", ""),
                    issue_code=issue.get("code")
                )
            )

    flake8 = static_results.get("flake8")

    if flake8:
        for issue in flake8.get("issues", []):
            issues.append(
                create_issue(
                    tool="Flake8",
                    line=issue.get("line"),
                    issue_type="Code Style",
                    message=issue.get("message", ""),
                    issue_code=issue.get("code")
                )
            )

    bandit = static_results.get("bandit")

    if bandit:
        for issue in bandit.get("issues", []):
            issues.append(
                create_issue(
                    tool="Bandit",
                    line=issue.get("line"),
                    issue_type="Security",
                    message=issue.get("message", ""),
                    issue_code=issue.get("code")
                )
            )

    return issues


def get_severity_summary(issues):
    summary = {
        "high": 0,
        "medium": 0,
        "low": 0
    }

    for issue in issues:
        severity = issue.get(
            "severity",
            "Low"
        ).lower()

        if severity == "high":
            summary["high"] += 1
        elif severity == "medium":
            summary["medium"] += 1
        else:
            summary["low"] += 1

    summary["total"] = (
        summary["high"]
        + summary["medium"]
        + summary["low"]
    )

    return summary


def sort_issues_by_severity(issues):
    priority = {
        "High": 1,
        "Medium": 2,
        "Low": 3
    }

    return sorted(
        issues,
        key=lambda issue: priority.get(
            issue.get("severity"),
            3
        )
    )