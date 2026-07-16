from celery import shared_task

from rule_engine.services import vocabulary_service


@shared_task
def rebuild_vocabulary():
    vocabulary_service.rebuild()
