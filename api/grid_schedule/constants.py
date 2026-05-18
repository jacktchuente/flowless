from django.db import models


class GridRecurrenceType(models.TextChoices):
    ALWAYS = "always", "always"
    DAILY = "daily", "daily"
    WEEKLY = "weekly", "weekly"
    MONTHLY = "monthly", "monthly"
    YEARLY = "yearly", "yearly"
    DATE_RANGE_DAILY = "date_range_daily", "date_range_daily"
    ONE_SHOT = "one_shot", "one_shot"


class ScheduleProgramType(models.TextChoices):
    MEDIA = "media", "media"
    FILLER = "filler", "filler"
    PROMO = "promo", "promo"
    AD_BREAK = "ad_break", "ad_break"
    FLEX = "flex", "flex"


class ScheduledContainerStatus(models.IntegerChoices):
    PENDING = 0, "pending"
    STARTED = 1, "started"
    PAUSED = 2, "paused"
    COMPLETED = 3, "completed"
    CANCELLED = 4, "cancelled"
    SKIPPED = 5, "skipped"
