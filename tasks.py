import os
import uuid

from datetime import datetime
from celery import Celery
from celery.utils.log import get_task_logger
from google.cloud import bigquery
from backtester.engine import BacktestEngine
from database.db import Session
from database.models import Backtest

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/etc/secrets/alduin-390505-cc185311f611.json'

class NoDataFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)
        logger.error(f"NoDataFoundException: {message}")

@app.task(bind=True)
def run_backtest(self, params):
    """
    Run a backtest using the provided parameters.

    Args:
        self: The task instance.
        params (dict): A dictionary containing the backtest parameters.

    Returns:
        dict: The unrealized results of the backtest.

    """
    task_id = self.request.id
    testing = params.get("testing", False)

    logger.info(f"Initializing backtest for task {task_id} w/ testing={testing} ...")
    backtester = BacktestEngine(start_date=params.get("start_date"),
                                end_date=params.get("end_date"),
                                sell_strike_method=params.get("sell_strike_method", "percent_under"),
                                portfolio_value=params.get("portfolio_value", 1000000),
                                spread=params.get("spread", 50))
    
    eval_data, unrealized_results = backtester.run()

    statistics_df = generate_statistics(unrealized_results)

    dataset_id = os.getenv('dataset_id')
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    table_name = f"{dataset_id}.unrealized_results_{timestamp}"

    # Save unrealized_results to BigQuery and metadata to Postgres
    if testing:
        logger.info(f"Testing mode: skipping upload to BigQuery and Postgres")
        return unrealized_results
    upload_to_bigquery(table_name, unrealized_results, 'unrealized_results.csv')
    save_to_postgres(task_id, table_name)
    return unrealized_results

def generate_statistics(unrealized_results):


def upload_to_bigquery(table_name, df, file_name):
    """
    Uploads a DataFrame to a BigQuery table.

    Args:
        table_name (str): The name of the BigQuery table.
        df (pandas.DataFrame): The DataFrame to upload.
        file_name (str): The name of the temporary CSV file to create.

    Raises:
        Exception: If the upload to BigQuery fails.

    Returns:
        None
    """
    logger.info(f'Uploading {file_name} to BigQuery table {table_name}...')
    df.to_csv(file_name, index=False)
    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
    )
    try:
        with open(file_name, 'rb') as source_file:
            job = client.load_table_from_file(source_file, table_name, job_config=job_config)
        job.result()
    except Exception as e:
        logger.error(f'Failed to upload {file_name} to BigQuery: {e}')
        raise
    finally:
        os.remove(file_name)

def save_to_postgres(task_id, table_name):
    """
    Save the task to the Postgres backtests table.

    Args:
        task_id (str): The ID of the task.
        table_name (str): The name of the table in Postgres.

    Raises:
        Exception: If there is an error while saving the task to Postgres.

    """
    logger.info(f'Saving task {task_id} to Postgres backtests table...')
    session = Session()
    try:
        new_backtest = Backtest(id=uuid.uuid4(),
                                task_id=task_id,
                                bigquery_table=table_name)
        session.add(new_backtest)
        session.commit()
    except Exception as e:
        logger.error(f'Failed to save task {task_id} to Postgres: {e}')
        raise
    finally:
        session.close()