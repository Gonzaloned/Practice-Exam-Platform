import logging
import time

from app import create_app
from app.extensions import db
from app.services.vm_environment import expire_due_exam_attempts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = create_app()


def run_cleanup_worker() -> None:
    interval = app.config.get("EXAM_SESSION_CLEANUP_INTERVAL_SECONDS", 30)
    while True:
        with app.app_context():
            try:
                processed_count = expire_due_exam_attempts()
                if processed_count:
                    logger.info("Cleaned up %s exam session(s)", processed_count)
            except Exception:
                db.session.rollback()
                logger.exception("Exam session cleanup pass failed")
        time.sleep(interval)


if __name__ == "__main__":
    run_cleanup_worker()
