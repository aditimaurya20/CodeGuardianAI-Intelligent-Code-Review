def clamp_score(score):
    return max(0, min(100, round(score, 2)))

def calculate_quality_score(
    pylint_result,
    flake8_result,
    bugs=None,
    issues=None
):
    pylint_issues = 0
    flake8_issues = 0
    bug_count = 0
    generic_issues = 0

    if pylint_result and pylint_result.get("success"):
        pylint_issues = pylint_result.get("total_issues", 0)

    if flake8_result and flake8_result.get("success"):
        flake8_issues = flake8_result.get("total_issues", 0)

    if bugs:
        bug_count = len(bugs)

    if issues:
        generic_issues = len(issues)

    if pylint_issues or flake8_issues or bug_count:
        penalty = (
            pylint_issues * 2
            + flake8_issues
            + bug_count * 5
        )
    else:
        penalty = generic_issues * 3

    return clamp_score(100 - penalty)

def calculate_security_score(bandit_result, issues=None):
    if not bandit_result:
        return None
    if not bandit_result.get("success"):
        return None
    high = bandit_result.get("high", 0)
    medium = bandit_result.get("medium", 0)
    low = bandit_result.get("low", 0)
    penalty = (
        high * 15
        + medium * 7
        + low * 2
    )
    return clamp_score(100 - penalty)
def calculate_complexity_score(radon_result, complexity=None):
    if radon_result:
        complexity_data = radon_result.get("complexity")

        if complexity_data:
            if not complexity_data.get("success"):
                return 0

            highest = complexity_data.get(
                "highest_complexity",
                0
            )

            if highest <= 5:
                return 100
            if highest <= 10:
                return 80
            if highest <= 20:
                return 60
            if highest <= 30:
                return 40
            return 20

    if complexity:
        loops = complexity.get("loops", 0)
        conditions = complexity.get("conditions", 0)

        score = 100 - (
            loops * 5
            + conditions * 3
        )

        return clamp_score(score)

    return 100

def calculate_maintainability_score(
    radon_result,
    metrics=None
):
    if radon_result:
        maintainability = radon_result.get(
            "maintainability"
        )

        if maintainability:
            if not maintainability.get("success"):
                return None

            score = maintainability.get(
                "maintainability_index"
            )

            if score is not None:
                return clamp_score(score)

    if metrics:
        total_lines = metrics.get("total_lines", 0)
        code_lines = metrics.get("code_lines", 0)
        loops = metrics.get("loops", 0)
        conditions = metrics.get("conditions", 0)

        penalty = 0

        if total_lines > 100:
            penalty += 10
        elif total_lines > 50:
            penalty += 5

        penalty += loops * 2
        penalty += conditions

        if code_lines:
            penalty += max(
                0,
                (code_lines - 20) // 20
            )

        return clamp_score(100 - penalty)

    return 100

def calculate_overall_score(
    quality_score,
    security_score,
    complexity_score,
    maintainability_score
):
    scores = [
        (quality_score, 0.35),
        (security_score, 0.30),
        (complexity_score, 0.15),
        (maintainability_score, 0.20)
    ]

    available_scores = [
        (score, weight)
        for score, weight in scores
        if score is not None
    ]

    if not available_scores:
        return None

    total_weight = sum(
        weight
        for _, weight in available_scores
    )

    score = sum(
        value * weight
        for value, weight in available_scores
    ) / total_weight

    return clamp_score(score)

def get_rating(score):
    if score is None:
        return "N/A"

    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Needs Improvement"

    return "Poor"

def get_score_message(score_type, score):
    messages = {
        "quality": (
            "Measures code quality based on "
            "static analysis issues and detected bugs."
        ),
        "security": (
            "Measures code security based on "
            "detected security vulnerabilities."
        ),
        "complexity": (
            "Measures how complex the code is. "
            "Lower complexity produces a higher score."
        ),
        "maintainability": (
            "Measures how easy the code is to "
            "understand, modify, and maintain."
        ),
        "overall": (
            "Combined score based on quality, "
            "security, complexity, and maintainability."
        )
    }

    return messages.get(
        score_type,
        "Code analysis score."
    )

def calculate_all_scores(
    pylint_result,
    flake8_result,
    bandit_result,
    radon_result,
    bugs=None,
    issues=None,
    complexity=None,
    metrics=None
):
    quality_score = calculate_quality_score(
        pylint_result,
        flake8_result,
        bugs,
        issues
    )

    security_score = calculate_security_score(
        bandit_result,
        issues
    )

    complexity_score = calculate_complexity_score(
        radon_result,
        complexity
    )

    maintainability_score = calculate_maintainability_score(
        radon_result,
        metrics
    )

    overall_score = calculate_overall_score(
        quality_score,
        security_score,
        complexity_score,
        maintainability_score
    )

    return {
        "quality": {
            "score": quality_score,
            "rating": get_rating(quality_score),
            "message": get_score_message(
                "quality",
                quality_score
            )
        },
        "security": {
            "score": security_score,
            "rating": get_rating(security_score),
            "message": get_score_message(
                "security",
                security_score
            )
        },
        "complexity": {
            "score": complexity_score,
            "rating": get_rating(complexity_score),
            "message": get_score_message(
                "complexity",
                complexity_score
            )
        },
        "maintainability": {
            "score": maintainability_score,
            "rating": get_rating(maintainability_score),
            "message": get_score_message(
                "maintainability",
                maintainability_score
            )
        },
        "overall": {
            "score": overall_score,
            "rating": get_rating(overall_score),
            "message": get_score_message(
                "overall",
                overall_score
            )
        }
    }