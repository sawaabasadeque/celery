import os
import time
from celery import Celery
from celery.utils.log import get_task_logger
from google.cloud import bigquery
from backtester.engine import BacktestEngine

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/etc/secrets/alduin-390505-cc185311f611.json'

class NoDataFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)
        logger.error(f"NoDataFoundException: {message}")

@app.task
def run_backtest(params):
    backtester = BacktestEngine(start_date=params.get("start_date"),
                                end_date=params.get("end_date"),
                                sell_strike_method=params.get("sell_strike_method", "percent_under"),
                                portfolio_value=params.get("portfolio_value", 1000000),
                                spread=params.get("spread", 50))
    eval_data, unrealized_results = backtester.run()
    logger.info('Backtest completed.')
    # Convert data into json for response
    data_json = data.to_json(orient='records')

    trades = backtesting_engine.simulate_trades()
    return trades

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