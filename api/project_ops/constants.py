from django.db import models


class AnalyzeStatus(models.IntegerChoices):
    IDLE = 0, "IDLE"
    ANALYZING = 1, "ANALYZING"
    COMPLETE = 2, "COMPLETE"
    SKIPPED = 3, "SKIPPED"
    COMPLETE_WITH_ERRORS = 4, "COMPLETE_WITH_ERRORS"
    CANCELLED = 5, "CANCELLED"
