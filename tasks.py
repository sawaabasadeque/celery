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
    task_id = self.request.id
    logger.info(f"Initializing backtest for task {task_id}")
    backtester = BacktestEngine(start_date=params.get("start_date"),
                                end_date=params.get("end_date"),
                                sell_strike_method=params.get("sell_strike_method", "percent_under"),
                                portfolio_value=params.get("portfolio_value", 1000000),
                                spread=params.get("spread", 50))
    
    eval_data, unrealized_results = backtester.run()

    # Save unrealized_results dataframe to BigQuery
    dataset_id = os.getenv('dataset_id')
    unrealized_results.to_csv('unrealized_results.csv', index=False)

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
    )

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    table_name = f"{dataset_id}.unrealized_results_{timestamp}"
    with open('unrealized_results.csv', 'rb') as source_file:
        job = client.load_table_from_file(source_file, table_name, job_config=job_config)
    job.result()
    os.remove('unrealized_results.csv')

    # Save backtest metadata to Postgres database
    session = Session()
    new_backtest = Backtest(id=uuid.uuid4(),
                            task_id=task_id,
                            bigquery_table=table_name)
    session.add(new_backtest)
    session.commit()

    return unrealized_results

def query_bigquery(sql_query):
    """Query the BigQuery database given a SQL query string."""

    # Create a "Client" object
    client = bigquery.Client()

    # Run the query, and convert the results to a pandas DataFrame
    query_job = client.query(sql_query)
    dataframe = query_job.to_dataframe()

    # If the dataframe is not empty, return it
    if not dataframe.empty:
        return dataframe
    else:
        raise NoDataFoundException(f"No data found for the provided query.")