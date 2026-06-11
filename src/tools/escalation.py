import logging

logger = logging.getLogger(__name__)


def escalate_to_human(reason: str, priority: str):
    logger.info(
        "Escalation requested: priority=%s reason=%s",
        priority,
        reason,
    )
