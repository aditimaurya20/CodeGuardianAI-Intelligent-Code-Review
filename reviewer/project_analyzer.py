from .analyzer import analyze_code


def analyze_project(files):
    """
    Analyze all supported files in a project and
    generate combined project-level results.
    """

    file_results = []

    total_files = 0
    successful_files = 0
    failed_files = 0

    total_lines = 0
    total_blank_lines = 0
    total_comment_lines = 0
    total_code_lines = 0

    total_issues = 0
    total_high = 0
    total_medium = 0
    total_low = 0

    total_loops = 0
    total_conditions = 0

    quality_scores = []

    for file_data in files:

        file_name = file_data.get("name", "")
        file_path = file_data.get("path", "")
        language = file_data.get("language", "Unknown")
        code = file_data.get("content", "")

        total_files += 1

        try:
            result = analyze_code(
                code,
                language
            )

            if result.get("success", True):
                successful_files += 1
            else:
                failed_files += 1

        except Exception as error:
            failed_files += 1

            result = {
                "success": False,
                "language": language,
                "issues": [],
                "total_static_issues": 0,
                "severity_summary": {
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "total": 0
                },
                "metrics": {
                    "total_lines": 0,
                    "blank_lines": 0,
                    "comment_lines": 0,
                    "code_lines": 0
                },
                "complexity": {
                    "loops": 0,
                    "conditions": 0,
                    "level": "Unknown",
                    "time_complexity": "Unknown"
                },
                "error": str(error)
            }

        # ---------------------------------------
        # FILE METRICS
        # ---------------------------------------

        metrics = result.get("metrics", {})

        total_lines += metrics.get(
            "total_lines",
            0
        )

        total_blank_lines += metrics.get(
            "blank_lines",
            0
        )

        total_comment_lines += metrics.get(
            "comment_lines",
            0
        )

        total_code_lines += metrics.get(
            "code_lines",
            0
        )

        # ---------------------------------------
        # ISSUES
        # ---------------------------------------

        severity = result.get(
            "severity_summary",
            {}
        )

        total_issues += severity.get(
            "total",
            result.get("total_static_issues", 0)
        )

        total_high += severity.get(
            "high",
            0
        )

        total_medium += severity.get(
            "medium",
            0
        )

        total_low += severity.get(
            "low",
            0
        )

        # ---------------------------------------
        # COMPLEXITY
        # ---------------------------------------

        complexity = result.get(
            "complexity",
            {}
        )

        total_loops += complexity.get(
            "loops",
            0
        )

        total_conditions += complexity.get(
            "conditions",
            0
        )

        # ---------------------------------------
        # QUALITY SCORE
        # ---------------------------------------

        quality_score = result.get(
            "quality_score"
        )

        if quality_score is None:

            scores = result.get(
                "scores",
                {}
            )

            quality_data = scores.get(
                "quality",
                {}
            )

            quality_score = quality_data.get(
                "score"
            )

        if isinstance(quality_score, (int, float)):
            quality_scores.append(
                quality_score
            )

        # ---------------------------------------
        # SAVE FILE RESULT
        # ---------------------------------------

        file_results.append({
            "name": file_name,
            "path": file_path,
            "language": language,
            "analysis": result
        })

    # -------------------------------------------
    # PROJECT QUALITY SCORE
    # -------------------------------------------

    if quality_scores:

        project_quality_score = round(
            sum(quality_scores) / len(quality_scores),
            2
        )

    else:
        project_quality_score = 0

    # -------------------------------------------
    # PROJECT COMPLEXITY
    # -------------------------------------------

    complexity_score = (
        total_loops +
        total_conditions
    )

    if complexity_score <= 5:
        complexity_level = "Low"

    elif complexity_score <= 15:
        complexity_level = "Medium"

    else:
        complexity_level = "High"

    # -------------------------------------------
    # PROJECT RESULT
    # -------------------------------------------

    project_result = {

        "total_files": total_files,

        "successful_files": successful_files,

        "failed_files": failed_files,

        "total_issues": total_issues,

        "severity_summary": {
            "high": total_high,
            "medium": total_medium,
            "low": total_low,
            "total": total_issues
        },

        "metrics": {
            "total_lines": total_lines,
            "blank_lines": total_blank_lines,
            "comment_lines": total_comment_lines,
            "code_lines": total_code_lines
        },

        "complexity": {
            "loops": total_loops,
            "conditions": total_conditions,
            "score": complexity_score,
            "level": complexity_level
        },

        "quality_score": project_quality_score,

        "files": file_results
    }

    return project_result