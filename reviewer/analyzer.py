from .pylint_analyzer import run_pylint
from .flake8_analyzer import run_flake8
from .bandit_analyzer import run_bandit
from .radon_analyzer import run_radon
from .score_analyzer import calculate_all_scores
from .ai_service import analyze_code_with_ai
from .severity_analyzer import (
    collect_all_issues,
    get_severity_summary,
    sort_issues_by_severity
)

def analyze_code(code, language):
    if language.lower() != "python":
        from .multi_language_analyzer import analyze_by_language
        language_result = analyze_by_language(
            code,
            language,
            "uploaded_code"
        )
        result = {
            "language": language,
            "ai_review": None,
            "pylint": None,
            "flake8": None,
            "bandit": None,
            "radon": None
        }
        result.update(language_result)
        lines = code.split("\n")
        total_lines = len(lines)
        blank_lines = 0
        comment_lines = 0
        code_lines = 0
        for line in lines:
            stripped_line = line.strip()
            if stripped_line == "":
                blank_lines += 1
            elif (
                stripped_line.startswith("#")
                or stripped_line.startswith("//")
                or stripped_line.startswith("/*")
                or stripped_line.startswith("*")
            ):
                comment_lines += 1
            else:
                code_lines += 1
        result["metrics"] = {
            "total_lines": total_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "code_lines": code_lines
        }
        loop_count = 0
        condition_count = 0
        for line in lines:
            stripped_line = line.strip()
            if (
                stripped_line.startswith("for ")
                or stripped_line.startswith("for(")
                or stripped_line.startswith("while ")
                or stripped_line.startswith("while(")
            ):
                loop_count += 1
            if (
                stripped_line.startswith("if ")
                or stripped_line.startswith("if(")
                or stripped_line.startswith("else if ")
                or stripped_line.startswith("else if(")
                or stripped_line.startswith("elif ")
                or stripped_line.startswith("elif(")
            ):
                condition_count += 1
        complexity_score = loop_count + condition_count
        if complexity_score <= 2:
            complexity_level = "Low"
        elif complexity_score <= 5:
            complexity_level = "Medium"
        else:
            complexity_level = "High"
        if loop_count >= 2:
            time_complexity = "O(n²)"
        elif loop_count == 1:
            time_complexity = "O(n)"
        else:
            time_complexity = "O(1)"
        result["complexity"] = {
            "loops": loop_count,
            "conditions": condition_count,
            "level": complexity_level,
            "time_complexity": time_complexity
        }
        result["issues"] = sort_issues_by_severity(
            language_result.get("issues", [])
        )
        result["severity_summary"] = get_severity_summary(
            result["issues"]
        )
        result["total_static_issues"] = len(result["issues"])
        result["scores"] = calculate_all_scores(
            None,
            None,
            None,
            None,
            None,
            result["issues"],
            result.get("complexity"),
            result.get("metrics")
        )
        result["quality_score"] = result["scores"]["quality"]["score"]
        print("AI REVIEW CALL STARTED")
        try:
            result["ai_review"] = analyze_code_with_ai(
                code,
                result,
                language
            )
        except Exception as e:
            print("AI REVIEW ERROR:", str(e))
            result["ai_review"] = {
                "success": False,
                "review": "",
                "error": str(e)
            }
        print(
            "AI REVIEW CALL FINISHED:",
            result["ai_review"].get("success"),
            "LENGTH:",
            len(result["ai_review"].get("review", ""))
        )
        return result

    result = {
        "language": language,
        "ai_review": None
    }

    # =====================================================
    # DEFAULT STATIC ANALYSIS RESULTS
    # =====================================================

    pylint_result = {
        "success": False,
        "issues": [],
        "total_issues": 0,
        "errors": 0,
        "warnings": 0,
        "conventions": 0,
        "refactors": 0
    }

    flake8_result = {
        "success": False,
        "issues": [],
        "total_issues": 0
    }

    bandit_result = {
        "success": False,
        "issues": [],
        "total_issues": 0
    }

    radon_result = {
        "success": False,
        "complexity": {},
        "maintainability": {}
    }

    # =====================================================
    # STATIC ANALYSIS
    # =====================================================

    if language.lower() == "python":
        pylint_result = run_pylint(
            code,
            filename="uploaded_code.py"
        )

        flake8_result = run_flake8(
            code,
            filename="uploaded_code.py"
        )

        bandit_result = run_bandit(
            code,
            filename="uploaded_code.py"
        )

        radon_result = run_radon(
            code,
            filename="uploaded_code.py"
        )

    result["pylint"] = pylint_result
    result["flake8"] = flake8_result
    result["bandit"] = bandit_result
    result["radon"] = radon_result

    # =====================================================
    # STATIC ISSUES
    # =====================================================

    # For Python, Pylint, Flake8 and Bandit
    # are combined into the static issue list.

    if language.lower() == "python":
        issues = []
        if pylint_result.get("success"):
            issues.extend(
                pylint_result.get("issues", [])
            )
        if flake8_result.get("success"):
            issues.extend(
                flake8_result.get("issues", [])
            )
        if bandit_result.get("success"):
            issues.extend(
                bandit_result.get("issues", [])
            )
    else:
        issues = result.get("issues", [])

    # =====================================================
    # CODE METRICS
    # =====================================================

    lines = code.split("\n")

    total_lines = len(lines)

    blank_lines = 0
    comment_lines = 0
    code_lines = 0

    for line in lines:
        stripped_line = line.strip()

        if stripped_line == "":
            blank_lines += 1

        elif (
            stripped_line.startswith("#")
            or stripped_line.startswith("//")
        ):
            comment_lines += 1

        else:
            code_lines += 1

    result["metrics"] = {
        "total_lines": total_lines,
        "blank_lines": blank_lines,
        "comment_lines": comment_lines,
        "code_lines": code_lines
    }

    # =====================================================
    # COMPLEXITY ANALYSIS
    # =====================================================

    loop_count = 0
    condition_count = 0

    for line in lines:
        line = line.strip()

        # Loops
        if (
            line.startswith("for ")
            or line.startswith("for(")
            or line.startswith("while ")
            or line.startswith("while(")
        ):
            loop_count += 1

        # Conditions
        if (
            line.startswith("if ")
            or line.startswith("if(")
            or line.startswith("elif ")
            or line.startswith("elif(")
        ):
            condition_count += 1

    complexity_score = loop_count + condition_count

    if complexity_score <= 2:
        complexity_level = "Low"

    elif complexity_score <= 5:
        complexity_level = "Medium"

    else:
        complexity_level = "High"

    # Basic time-complexity estimate
    if loop_count >= 2:
        time_complexity = "O(n²)"

    elif loop_count == 1:
        time_complexity = "O(n)"

    else:
        time_complexity = "O(1)"

    result["complexity"] = {
        "loops": loop_count,
        "conditions": condition_count,
        "level": complexity_level,
        "time_complexity": time_complexity
    }

    # =====================================================
    # QUALITY SCORE
    # =====================================================

    score = 100

    if (
        language.lower() == "python"
        and pylint_result.get("success")
    ):
        score -= pylint_result.get("errors", 0) * 8
        score -= pylint_result.get("warnings", 0) * 4
        score -= pylint_result.get("conventions", 0) * 2
        score -= pylint_result.get("refactors", 0)

    score -= loop_count * 2
    score -= condition_count

    score = max(0, min(100, score))

    result["quality_score"] = score

    # =====================================================
    # FINAL STATIC ISSUES
    # =====================================================

    result["total_static_issues"] = len(issues)

    result["issues"] = collect_all_issues(
        result
    )

    result["issues"] = sort_issues_by_severity(
        result["issues"]
    )

    result["severity_summary"] = get_severity_summary(
        result["issues"]
    )

    # =====================================================
    # SCORE ENGINE
    # =====================================================

    result["scores"] = calculate_all_scores(
        result.get("pylint"),
        result.get("flake8"),
        result.get("bandit"),
        result.get("radon"),
        result.get("bugs"),
        result.get("issues"),
        result.get("complexity"),
        result.get("metrics")
    )

    # =====================================================
    # AI CODE REVIEW
    # =====================================================
    print("AI REVIEW CALL STARTED")
    try:
        result["ai_review"] = analyze_code_with_ai(
            code,
            result,
            language
        )
    except Exception as e:
        print("AI REVIEW ERROR:", str(e))
        result["ai_review"] = {
            "success": False,
            "review": "",
            "error": str(e)
        }
    print(
        "AI REVIEW CALL FINISHED:",
        result["ai_review"].get("success")
    )
    return result

def analyze_optimized_code(code, language):
    if not code or not code.strip():
        return {}
    if language.lower() != "python":
        from .multi_language_analyzer import analyze_by_language
        language_result = analyze_by_language(
            code,
            language,
            "optimized_code"
        )
        issues = language_result.get("issues", [])
        complexity = {
            "loops": 0,
            "conditions": 0,
            "level": "Low",
            "time_complexity": "O(1)"
        }
        lines = code.split("\n")
        total_lines = len(lines)
        blank_lines = 0
        comment_lines = 0
        code_lines = 0
        loop_count = 0
        condition_count = 0
        for line in lines:
            stripped_line = line.strip()
            if stripped_line == "":
                blank_lines += 1
            elif (
                stripped_line.startswith("#")
                or stripped_line.startswith("//")
                or stripped_line.startswith("/*")
                or stripped_line.startswith("*")
            ):
                comment_lines += 1
            else:
                code_lines += 1
            if (
                stripped_line.startswith("for ")
                or stripped_line.startswith("for(")
                or stripped_line.startswith("while ")
                or stripped_line.startswith("while(")
            ):
                loop_count += 1
            if (
                stripped_line.startswith("if ")
                or stripped_line.startswith("if(")
                or stripped_line.startswith("else if ")
                or stripped_line.startswith("else if(")
                or stripped_line.startswith("elif ")
                or stripped_line.startswith("elif(")
            ):
                condition_count += 1
        complexity_score = loop_count + condition_count
        if complexity_score <= 2:
            complexity["level"] = "Low"
        elif complexity_score <= 5:
            complexity["level"] = "Medium"
        else:
            complexity["level"] = "High"
        if loop_count >= 2:
            complexity["time_complexity"] = "O(n²)"
        elif loop_count == 1:
            complexity["time_complexity"] = "O(n)"
        result = {
            "language": language,
            "pylint": None,
            "flake8": None,
            "bandit": None,
            "radon": None,
            "issues": issues,
            "total_static_issues": len(issues),
            "severity_summary": language_result.get(
                "severity_summary",
                {
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "total": len(issues)
                }
            ),
            "metrics": {
                "total_lines": total_lines,
                "blank_lines": blank_lines,
                "comment_lines": comment_lines,
                "code_lines": code_lines
            },
            "complexity": complexity
        }
        result["scores"] = calculate_all_scores(
            None,
            None,
            None,
            None,
            None,
            issues,
            complexity,
            result["metrics"]
        )
        return result
    pylint_result = run_pylint(
        code,
        filename="optimized_code.py"
    )
    flake8_result = run_flake8(
        code,
        filename="optimized_code.py"
    )
    bandit_result = run_bandit(
        code,
        filename="optimized_code.py"
    )
    radon_result = run_radon(
        code,
        filename="optimized_code.py"
    )
    result = {
        "language": language,
        "pylint": pylint_result,
        "flake8": flake8_result,
        "bandit": bandit_result,
        "radon": radon_result
    }
    result["issues"] = collect_all_issues(result)
    result["severity_summary"] = {
        "high": 0,
        "medium": 0,
        "low": 0,
        "total": len(result["issues"])
    }
    for issue in result["issues"]:
        severity = issue.get("severity", "Low").lower()
        if severity == "high":
            result["severity_summary"]["high"] += 1
        elif severity == "medium":
            result["severity_summary"]["medium"] += 1
        else:
            result["severity_summary"]["low"] += 1
    result["total_static_issues"] = len(
        result["issues"]
    )
    result["scores"] = calculate_all_scores(
        pylint_result,
        flake8_result,
        bandit_result,
        radon_result,
        None,
        result["issues"],
        result.get("complexity"),
        result.get("metrics")
    )
    return result