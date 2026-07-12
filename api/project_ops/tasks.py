from celery import shared_task

from project_ops.services.heartbeat import record_heartbeat


@shared_task
def heartbeat():
    record_heartbeat()
