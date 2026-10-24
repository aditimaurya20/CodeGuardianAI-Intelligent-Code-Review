import os
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import CodeFile, AnalysisHistory
from .ai_service import process_ai_response
import time
from .analyzer import analyze_code, analyze_optimized_code
from .project_analyzer import analyze_project
from .github_service import get_repository_files
from .multi_language_analyzer import analyze_by_language, detect_language
from io import BytesIO
from html import escape
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from .optimization import (
    clean_optimized_code,
    calculate_difference,
    calculate_issue_difference,
    calculate_overall_improvement
)
import logging
logger = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {
    ".py",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".java"
}
MAX_FILE_SIZE = 2 * 1024 * 1024

def home(request):
    return render(request, 'home.html')

def login_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(
            request,
            username=username,
            password=password
        )
        if user is not None:
            login(request, user)
            return redirect('/upload/')
        return render(
            request,
            'login.html',
            {
                'error': 'Invalid Username or Password'
            }
        )
    return render(request, 'login.html')

def register_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(
                request,
                'register.html',
                {
                    'error': 'Passwords do not match'
                }
            )
        if User.objects.filter(username=username).exists():
            return render(
                request,
                'register.html',
                {
                    'error': 'Username already exists'
                }
            )
        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        return redirect('/login/')
    return render(request, 'register.html')

@login_required(login_url='/login/')
def upload_page(request):
    if request.method == "POST":
        # GitHub repository analysis
        if request.POST.get("action") == "analyze_github":
            repository_url = request.POST.get(
                "repository_url", ""
            ).strip()

            if not repository_url.startswith(
                ("https://github.com/", "http://github.com/")
            ):
                return render(
                    request,
                    'upload.html',
                    {
                        'github_error': 'Please enter a valid GitHub repository URL.',
                        'repository_url': repository_url,
                    }
                )

            try:
                github_result = get_repository_files(repository_url)

                if not github_result.get("success"):
                    return render(
                        request,
                        'upload.html',
                        {
                            'github_error': github_result.get(
                                "error",
                                "Could not access the GitHub repository."
                            ),
                            'repository_url': repository_url,
                        }
                    )

                files = github_result.get("files", [])

                if not files:
                    return render(
                        request,
                        'upload.html',
                        {
                            'github_error': 'No supported source-code files were found.',
                            'repository_url': repository_url,
                        }
                    )
                project_analysis = analyze_project(files)
                request.session["github_pdf_data"] = {
                    "repository": github_result.get("repository", repository_url),
                    "repository_url": repository_url,
                    **project_analysis,
                }
                request.session.modified = True

                return render(
                    request,
                    'github_result.html',
                    {
                        'repository': github_result.get(
                            "repository", repository_url
                        ),
                        'repository_url': repository_url,
                        'project_analysis': project_analysis,
                    }
                )

            except Exception:
                return render(
                    request,
                    'upload.html',
                    {
                        'github_error': (
                            'Repository analysis failed. Please check the URL '
                            'and try again.'
                        ),
                        'repository_url': repository_url,
                    }
                )

        # Existing single-file upload functionality
        uploaded_file = request.FILES.get('code_file')
        selected_language = request.POST.get('language')

        if not uploaded_file:
            return render(
                request,
                'upload.html',
                {'error': 'Please select a file.'}
            )

        extension = os.path.splitext(uploaded_file.name)[1].lower()

        language_extensions = {
            "Python": [".py"],
            "C++": [".cpp", ".cc", ".cxx", ".h", ".hpp"],
            "Java": [".java"]
        }

        if selected_language not in language_extensions:
            return render(
                request,
                'upload.html',
                {'error': 'Please select a valid programming language.'}
            )

        if extension not in ALLOWED_EXTENSIONS:
            return render(
                request,
                'upload.html',
                {'error': 'Unsupported file type. Allowed: Python, C++, Java.'}
            )

        if extension not in language_extensions[selected_language]:
            return render(
                request,
                'upload.html',
                {
                    'error': (
                        f'The selected language "{selected_language}" '
                        f'does not match the uploaded file type.'
                    )
                }
            )

        if uploaded_file.size > MAX_FILE_SIZE:
            return render(
                request,
                'upload.html',
                {'error': 'File size must not exceed 2 MB.'}
            )

        try:
            code_content = uploaded_file.read().decode('utf-8')
        except UnicodeDecodeError:
            return render(
                request,
                'upload.html',
                {'error': 'File must be a valid UTF-8 text file.'}
            )

        if not code_content.strip():
            return render(
                request,
                'upload.html',
                {'error': 'The uploaded file is empty.'}
            )

        detected_language = detect_language(uploaded_file.name)

        code_file = CodeFile.objects.create(
            file=uploaded_file,
            language=detected_language
        )
        request.session['file_id'] = code_file.id
        return redirect('/result/')
    return render(request, 'upload.html')

def save_analysis_history(
    user,
    code_file,
    analysis_result,
    ai_review_data
):
    scores = analysis_result.get("scores") or {}
    severity_summary = analysis_result.get("severity_summary") or {}

    if not isinstance(ai_review_data, dict):
        ai_review_data = {}

    def get_score(score_name):
        value = scores.get(score_name)
        if isinstance(value, dict):
            return value.get("score") or 0
        if isinstance(value, (int, float)):
            return value
        return 0

    history = AnalysisHistory.objects.create(
        user=user,
        code_file=code_file,
        file_name=code_file.file.name,
        language=analysis_result.get(
            "language",
            code_file.language
        ),
        quality_score=get_score("quality"),
        security_score=get_score("security"),
        complexity_score=get_score("complexity"),
        maintainability_score=get_score("maintainability"),
        overall_score=get_score("overall"),
        high_issues=severity_summary.get(
            "high",
            0
        ),
        medium_issues=severity_summary.get(
            "medium",
            0
        ),
        low_issues=severity_summary.get(
            "low",
            0
        ),
        total_issues=severity_summary.get(
            "total",
            0
        ),
        issues=analysis_result.get(
            "issues",
            []
        ),
        pylint_results=analysis_result.get("pylint") or {},
        flake8_results=analysis_result.get("flake8") or {},
        bandit_results=analysis_result.get("bandit") or {},
        radon_results=analysis_result.get("radon") or {},
        bugs=ai_review_data.get(
            "bugs",
            ""
        ),
        code_quality=ai_review_data.get(
            "quality",
            ""
        ),
        performance=ai_review_data.get(
            "performance",
            ""
        ),
        security=ai_review_data.get(
            "security",
            ""
        ),
        suggestions=ai_review_data.get(
            "suggestions",
            ""
        ),
        ai_review=ai_review_data.get(
            "review",
            ""
        ),
        optimized_code=ai_review_data.get(
            "optimized_code",
            ""
        )
    )

    return history

@login_required(login_url='/login/')
def result_page(request):
    file_id = request.session.get('file_id')
    code_content = ""
    analysis = {}
    ai_review = {}
    scores = {}
    optimization_comparison = {}
    if file_id:
        code_file = get_object_or_404(
            CodeFile,
            id=file_id
        )
        with open(code_file.file.path, 'r', encoding='utf-8') as file:
            code_content = file.read()
        if not code_content.strip():
            return render(
                request,
                'result.html',
                {
                    'code_content': '',
                    'analysis': {},
                    'ai_review': {
                        'success': False,
                        'review': '',
                        'error': 'No code was provided.'
                    },
                    'scores': {},
                    'issues': [],
                    'severity_summary': {},
                    'optimization_comparison': {}
                }
            )
        start = time.time()
        try:
            analysis = analyze_code(
                code_content,
                code_file.language
            )
            analysis["language"] = code_file.language
            scores = analysis.get("scores", {})

            logger.info(
                "STATIC ANALYSIS TIME: %.2f seconds",
                time.time() - start
            )
        except Exception as e:
            analysis = {
                'language': code_file.language,
                'metrics': {},
                'complexity': {},
                'quality_score': 0,
                'issues': [],
                'total_static_issues': 0,
                'severity_summary': {
                    'high': 0,
                    'medium': 0,
                    'low': 0,
                    'total': 0
                },
                'pylint': {},
                'flake8': {},
                'bandit': {},
                'radon': {},
                'scores': {},
                'ai_review': {
                    'success': False,
                    'review': '',
                    'error': str(e)
                }
            }
            scores = {}
        ai_start = time.time()
        ai_response = analysis.get(
            'ai_review') or {
                'success': False,
                'review': '',
                'error': 'AI review unavailable.'
            }
        ai_review = process_ai_response(
            ai_response.get('review', '')
        )
        ai_review['bugs_count'] = len(
            ai_review.get('bugs', '').splitlines()
        )
        ai_review['security_count'] = len(
            ai_review.get('security', '').splitlines()
        )
        ai_review['success'] = ai_response.get(
            'success',
            False
        )
        ai_review['error'] = ai_response.get(
            'error',
            ''
        )
        optimized_code = clean_optimized_code(
            ai_review.get('optimized_code', '')
        )
        optimized_analysis = {}
        if optimized_code:
            try:
                optimized_analysis = analyze_optimized_code(
                    optimized_code,
                    code_file.language
                )
            except Exception as e:
                logger.exception(
                    "OPTIMIZED CODE ANALYSIS ERROR: %s",
                    e
                )
        before_scores = {}
        after_scores = {}
        comparison_available = bool(
            scores
            and optimized_analysis.get('scores')
        )
        if comparison_available:
            before_scores = {
                "quality": scores.get(
                    "quality",
                    {}
                ).get("score"),
                "security": scores.get(
                    "security",
                    {}
                ).get("score"),
                "complexity": scores.get(
                    "complexity",
                    {}
                ).get("score"),
                "maintainability": scores.get(
                    "maintainability",
                    {}
                ).get("score")
            }
            after_scores = {
                "quality": optimized_analysis.get(
                    "scores",
                    {}
                ).get(
                    "quality",
                    {}
                ).get("score"),
                "security": optimized_analysis.get(
                    "scores",
                    {}
                ).get(
                    "security",
                    {}
                ).get("score"),
                "complexity": optimized_analysis.get(
                    "scores",
                    {}
                ).get(
                    "complexity",
                    {}
                ).get("score"),
                "maintainability": optimized_analysis.get(
                    "scores",
                    {}
                ).get(
                    "maintainability",
                    {}
                ).get("score")
            }
            available_metrics = [
                metric
                for metric in before_scores
                if before_scores.get(metric) is not None
                and after_scores.get(metric) is not None
            ]

            if available_metrics:
                comparison_before = {
                    metric: before_scores[metric]
                    for metric in available_metrics
                }
                comparison_after = {
                    metric: after_scores[metric]
                    for metric in available_metrics
                }
                comparison = calculate_difference(
                    comparison_before,
                    comparison_after
                )
                overall_comparison = calculate_overall_improvement(
                    comparison_before,
                    comparison_after
                )
                for metric in before_scores:
                    if (
                        before_scores.get(metric) is None
                        or after_scores.get(metric) is None
                    ):
                        comparison[metric] = {
                            "before": None,
                            "after": None,
                            "difference": None
                        }
                optimization_comparison["scores"] = comparison
                optimization_comparison["overall"] = overall_comparison
        issue_comparison = calculate_issue_difference(
            analysis.get("issues", []),
            optimized_analysis.get("issues", [])
        )
        optimization_comparison["issues"] = issue_comparison
        optimization_comparison["available"] = comparison_available
        optimization_comparison["language"] = code_file.language
        if not comparison_available:
            optimization_comparison["message"] = (
                "Score comparison is not available for "
                f"{code_file.language}."
            )
        logger.info(
            "AI REVIEW TIME: %.2f seconds",
            time.time() - ai_start
        )
        save_analysis_history(
            request.user,
            code_file,
            analysis,
            ai_review
        )
    return render(
        request,
        'result.html',
        {
            'code_content': code_content,
            'analysis': analysis,
            'ai_review': ai_review,
            'scores': scores,
            'issues': analysis.get(
                'issues',
                []
            ),
            'severity_summary': analysis.get(
                'severity_summary',
                {}
            ),
            'optimization_comparison': optimization_comparison
        }
    )

@login_required(login_url='/login/')
def download_result_pdf(request):
    print("DEBUG: download_result_pdf function started")

    file_id = request.session.get('file_id')
    print("DEBUG: file_id =", file_id)

    if not file_id:
        return HttpResponse(
            "Analysis report nahi mili. Please file ko dobara analyze karo.",
            status=400
        )

    code_file = get_object_or_404(CodeFile, id=file_id)

    history = AnalysisHistory.objects.filter(
        user=request.user,
        code_file=code_file
    ).order_by('-created_at').first()

    if not history:
        return HttpResponse(
            "Saved analysis report nahi mili. Please code ko dobara analyze karo.",
            status=404
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35,
    )

    styles = getSampleStyleSheet()
    story = []

    def add_text(value, style="BodyText"):
        value = escape(str(value if value is not None else "N/A"))
        story.append(Paragraph(value, styles[style]))
        story.append(Spacer(1, 6))

    add_text("Code Guardian AI", "Title")
    add_text("Intelligent Code Review Report", "Heading1")
    add_text(f"File: {os.path.basename(history.file_name)}")
    add_text(f"Language: {history.language}")

    add_text("Analysis Summary", "Heading2")
    add_text(f"Quality Score: {history.quality_score}")
    add_text(f"Security Score: {history.security_score}")
    add_text(f"Complexity Score: {history.complexity_score}")
    add_text(f"Maintainability Score: {history.maintainability_score}")
    add_text(f"Overall Score: {history.overall_score}")

    add_text("Issue Summary", "Heading2")
    add_text(f"High: {history.high_issues}")
    add_text(f"Medium: {history.medium_issues}")
    add_text(f"Low: {history.low_issues}")
    add_text(f"Total Issues: {history.total_issues}")

    add_text("Detected Issues", "Heading2")
    issues = history.issues or []

    if issues:
        rows = [["Severity", "Line", "Type", "Description"]]

        for issue in issues:
            rows.append([
                Paragraph(escape(str(issue.get("severity", "N/A"))), styles["BodyText"]),
                Paragraph(escape(str(issue.get("line", "-"))), styles["BodyText"]),
                Paragraph(escape(str(issue.get("type") or issue.get("code") or "-")), styles["BodyText"]),
                Paragraph(escape(str(issue.get("message", "N/A"))), styles["BodyText"]),
            ])

        table = Table(
            rows,
            colWidths=[65, 35, 85, 295],
            repeatRows=1
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263547")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)
    else:
        add_text("No issues detected.")

    add_text("AI Code Review", "Heading2")
    for label, value in [
        ("Bugs", history.bugs),
        ("Code Quality", history.code_quality),
        ("Performance", history.performance),
        ("Security", history.security),
        ("Suggestions", history.suggestions),
    ]:
        add_text(label, "Heading3")
        add_text(value or "Not available.")

        # Build PDF only after all files have been added
        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/pdf"
        )

        
        # Get the original uploaded filename
        original_name = os.path.basename(
            code_file.file.name or history.file_name or "code-review"
        )

        # Remove the file extension before adding the report suffix
        file_name = os.path.splitext(original_name)[0]

        # Remove the random suffix, if present
        file_name = re.sub(r"_\w{6}$", "", file_name)

        # Make filename safe
        file_name = re.sub(r"[^A-Za-z0-9._-]", "_", file_name)
        file_name = file_name or "code-review"

        response["Content-Disposition"] = (
            f'attachment; filename="{file_name}-Code-Review.pdf"'
        )
    return response

@login_required(login_url='/login/')
def history_page(request):
    histories = AnalysisHistory.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        'history.html',
        {
            'histories': histories
        }
    )


@login_required(login_url='/login/')
def history_detail(request, history_id):
    history = get_object_or_404(
        AnalysisHistory,
        id=history_id,
        user=request.user
    )

    ai_review = {
        "bugs": history.bugs,
        "quality": history.code_quality,
        "performance": history.performance,
        "security": history.security,
        "suggestions": history.suggestions,
        "optimized_code": history.optimized_code
    }

    return render(
        request,
        'history_detail.html',
        {
            'history': history,
            'ai_review': ai_review
        }
    )

def logout_page(request):
    logout(request)
    return redirect('/')


@login_required(login_url='/login/')
def github_project(request):
    if request.method == "POST":
        repository_url = request.POST.get(
            "repository_url", ""
        ).strip()

        if not repository_url.startswith(
            ("https://github.com/", "http://github.com/")
        ):
            return render(
                request,
                "github_project.html",
                {"error": "Please enter a valid GitHub repository URL."}
            )

        try:
            github_result = get_repository_files(repository_url)

            if not github_result.get("success"):
                return render(
                    request,
                    "github_project.html",
                    {
                        "error": github_result.get(
                            "error", "Could not access repository."
                        ),
                        "repository_url": repository_url,
                    }
                )

            files = github_result.get("files", [])

            if not files:
                return render(
                    request,
                    "github_project.html",
                    {
                        "error": "No supported source-code files found.",
                        "repository_url": repository_url,
                    }
                )

            project_analysis = analyze_project(files)
            request.session["github_pdf_data"] = {
                "repository": github_result.get("repository", repository_url),
                "repository_url": repository_url,
                **project_analysis,
            }
            request.session.modified = True
            return render(
                request,
                "github_project.html",
                {
                    "repository": github_result.get("repository", ""),
                    "repository_url": repository_url,
                    "project_analysis": project_analysis,
                }
            )

        except Exception:
            logger.exception("GitHub project analysis failed")
            return render(
                request,
                "github_project.html",
                {
                    "error": "Repository analysis failed. Please try again.",
                    "repository_url": repository_url,
                }
            )

    return render(request, "github_project.html")

@login_required(login_url='/login/')
def download_github_pdf(request):
    from reportlab.platypus import KeepTogether

    data = request.session.get("github_pdf_data")

    if not data:
        return HttpResponse(
            "Report data nahi mila. Please GitHub repository ko dobara analyze karo.",
            status=400
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35,
    )

    styles = getSampleStyleSheet()
    story = []

    def add_text(value, style="BodyText"):
        safe_value = escape(str(value if value is not None else "N/A"))
        story.append(Paragraph(safe_value, styles[style]))
        story.append(Spacer(1, 6))

    add_text("Code Guardian AI", "Title")
    add_text("GitHub Project Review Report", "Heading1")
    add_text("Repository: " + str(data.get("repository", "Unknown")))
    add_text("Repository URL: " + str(data.get("repository_url", "N/A")))

    add_text("Project Summary", "Heading2")

    summary = [
        ["Metric", "Result"],
        ["Total Files", data.get("total_files", 0)],
        ["Successfully Analyzed", data.get("successful_files", 0)],
        ["Failed Files", data.get("failed_files", 0)],
        ["Quality Score", str(data.get("quality_score", "N/A")) + "%"],
        ["Total Issues", data.get("total_issues", 0)],
    ]

    table = Table(summary, colWidths=[250, 230], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263547")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)
    story.append(Spacer(1, 15))

    metrics = data.get("metrics") or {}
    complexity = data.get("complexity") or {}
    severity = data.get("severity_summary") or {}

    add_text("Project Metrics", "Heading2")
    for label, key in [
        ("Total Lines", "total_lines"),
        ("Code Lines", "code_lines"),
        ("Blank Lines", "blank_lines"),
        ("Comment Lines", "comment_lines"),
    ]:
        add_text(f"{label}: {metrics.get(key, 0)}")

    add_text("Complexity", "Heading2")
    add_text(f"Loops: {complexity.get('loops', 0)}")
    add_text(f"Conditions: {complexity.get('conditions', 0)}")
    add_text(f"Level: {complexity.get('level', 'N/A')}")
    add_text(f"Score: {complexity.get('score', 0)}")

    add_text("Issue Severity", "Heading2")
    for level in ("high", "medium", "low"):
        add_text(f"{level.title()}: {severity.get(level, 0)}")

    add_text("File-by-File Analysis", "Heading1")

    for file_data in data.get("files", []):
        add_text(
            file_data.get("path") or file_data.get("name", "Unknown file"),
            "Heading2"
        )

        add_text("Language: " + str(file_data.get("language", "Unknown")))

        analysis = file_data.get("analysis") or {}
        file_metrics = analysis.get("metrics") or {}

        add_text(f"Total Lines: {file_metrics.get('total_lines', 0)}")
        add_text(
            "Quality Score: " +
            str(analysis.get("quality_score", "N/A"))
        )

        issues = analysis.get("issues") or []
        if issues:
            issue_rows = [["Severity", "Line", "Type", "Description"]]

            for issue in issues:
                issue_rows.append([
                    str(issue.get("severity", "Unknown")),
                    str(issue.get("line", "-")),
                    str(issue.get("type") or issue.get("code") or "-"),
                    str(issue.get("message", "No description")),
                ])

            formatted_rows = []
            for row_index, row in enumerate(issue_rows):
                if row_index == 0:
                    formatted_rows.append([
                        Paragraph(escape(cell), styles["BodyText"])
                        for cell in row
                    ])
                else:
                    formatted_rows.append([
                        Paragraph(escape(cell), styles["BodyText"])
                        for cell in row
                    ])

            issue_table = Table(
                formatted_rows,
                colWidths=[65, 35, 75, 305],
                repeatRows=1,
            )
            issue_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263547")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(issue_table)
            story.append(Spacer(1, 12))
        else:
            add_text("No issues reported for this file.")

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(),content_type="application/pdf")

        repo_name = data.get("repository", "github-repository")
        repo_name = repo_name.rstrip("/").split("/")[-1]
        repo_name = re.sub(r"[^A-Za-z0-9._-]", "_", repo_name)
        repo_name = repo_name or "github-repository"

        response["Content-Disposition"] = (
            f'attachment; filename="{repo_name}-Code-Review.pdf"'
        )

    return response