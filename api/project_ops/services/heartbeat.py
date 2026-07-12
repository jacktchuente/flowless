import time

import redis
from django.conf import settings

HEARTBEAT_KEY = "flowless:scheduler-heartbeat"
# La tache "Scheduler heartbeat" tourne chaque minute : au-dela de 3 intervalles
# sans battement, beat ou le worker est considere mort.
HEARTBEAT_MAX_AGE_SECONDS = 180


def _client():
    return redis.Redis.from_url(settings.CELERY_BROKER_URL)


def record_heartbeat():
    _client().set(HEARTBEAT_KEY, str(time.time()))


def heartbeat_age_seconds():
    raw = _client().get(HEARTBEAT_KEY)
    if raw is None:
        return None
    return time.time() - float(raw)


def scheduler_is_alive():
    """Retourne (alive, age_seconds). Un battement recent prouve a la fois que
    beat planifie et que le worker execute."""
    try:
        age = heartbeat_age_seconds()
    except (redis.RedisError, ValueError):
        return False, None
    if age is None:
        return False, None
    return age <= HEARTBEAT_MAX_AGE_SECONDS, age
