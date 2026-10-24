from django.db import models

class CodeFile(models.Model):

    file = models.FileField(
        upload_to='code_files/'
    )

    language = models.CharField(
        max_length=50,
        default="Unknown"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return self.file.name


class AnalysisHistory(models.Model):

    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE
    )

    code_file = models.ForeignKey(
        CodeFile,
        on_delete=models.CASCADE
    )

    file_name = models.CharField(
        max_length=255,
        blank=True
    )

    language = models.CharField(
        max_length=50,
        default="Unknown"
    )

    # =========================
    # SCORES
    # =========================

    quality_score = models.FloatField(
        default=0
    )

    security_score = models.FloatField(
        default=0
    )

    complexity_score = models.FloatField(
        default=0
    )

    maintainability_score = models.FloatField(
        default=0
    )

    overall_score = models.FloatField(
        default=0
    )

    # =========================
    # ISSUE COUNTS
    # =========================

    high_issues = models.IntegerField(
        default=0
    )

    medium_issues = models.IntegerField(
        default=0
    )

    low_issues = models.IntegerField(
        default=0
    )

    total_issues = models.IntegerField(
        default=0
    )

    # =========================
    # DETAILED ANALYSIS
    # =========================

    issues = models.JSONField(
        default=list,
        blank=True
    )

    pylint_results = models.JSONField(
        default=dict,
        blank=True
    )

    flake8_results = models.JSONField(
        default=dict,
        blank=True
    )

    bandit_results = models.JSONField(
        default=dict,
        blank=True
    )

    radon_results = models.JSONField(
        default=dict,
        blank=True
    )

    # =========================
    # AI REVIEW
    # =========================

    bugs = models.TextField(
        blank=True
    )

    code_quality = models.TextField(
        blank=True
    )

    performance = models.TextField(
        blank=True
    )

    security = models.TextField(
        blank=True
    )

    suggestions = models.TextField(
        blank=True
    )

    ai_review = models.TextField(
        blank=True
    )

    optimized_code = models.TextField(
        blank=True
    )

    # =========================
    # TIMESTAMP
    # =========================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = [
            "-created_at"
        ]

    def __str__(self):

        return (
            f"{self.file_name or self.code_file.file.name}"
            f" - {self.user.username}"
        )