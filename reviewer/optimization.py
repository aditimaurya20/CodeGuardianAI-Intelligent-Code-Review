from .score_analyzer import calculate_overall_score
def clean_optimized_code(code):
    if not code:
        return ""
    code = code.strip()
    lines = code.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()

def calculate_difference(before, after):
    """Calculate before vs after score differences."""
    difference = {}
    metrics = [
        "quality",
        "security",
        "complexity",
        "maintainability",
    ]
    for metric in metrics:
        before_value = before.get(metric, 0)
        after_value = after.get(metric, 0)
        difference[metric] = {
            "before": before_value,
            "after": after_value,
            "change": after_value - before_value,
        }
    return difference

def calculate_issue_difference(before_issues, after_issues):
    """Calculate before vs after issue counts."""
    before_count = len(before_issues)
    after_count = len(after_issues)

    return {
        "before": before_count,
        "after": after_count,
        "change": after_count - before_count,
        "reduced": before_count - after_count,
    }

def calculate_overall_improvement(before, after):
    before_overall = calculate_overall_score(
        before.get("quality"),
        before.get("security"),
        before.get("complexity"),
        before.get("maintainability")
    )
    after_overall = calculate_overall_score(
        after.get("quality"),
        after.get("security"),
        after.get("complexity"),
        after.get("maintainability")
    )
    return {
        "before": before_overall,
        "after": after_overall,
        "difference": (
            round(after_overall - before_overall, 2)
            if before_overall is not None
            and after_overall is not None
            else None
        )
    }