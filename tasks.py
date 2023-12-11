import os
from celery import Celery
from celery.utils.log import get_task_logger

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)

@app.task
def run_backtest(params):
    logger.info('Beginning backtest...')
    pass