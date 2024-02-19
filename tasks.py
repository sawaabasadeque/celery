import os
import uuid
import pandas as pd
import numpy as np
from functools import wraps
from datetime import datetime
from celery import Celery
from celery.utils.log import get_task_logger
from google.cloud import bigquery
from backtester.engine import BacktestEngine
from database.db import Session
from database.models import Backtest, Statistic

from utils import calculate_total_return, calculate_max_drawdown, calculate_portfolio_std

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv("gcp_credentials_path")

class NoDataFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)
        logger.error(f"NoDataFoundException: {message}")

def update_error_status(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            task_id = args[0].request.id
            params = args[1]
            backtest_id = params.get('backtest_id')
            logger.error(f'Error running backtest {task_id}: {e}')
            error_status_update(backtest_id)
            raise
    return wrapper

@app.task(bind=True)
@update_error_status
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
    backtest_id = params.get('backtest_id')
    testing = params.get("testing", False)
    initial_portfolio_value = params.get("portfolio_value", 1000000)

    logger.info(f"Initializing backtest for task {task_id} w/ testing={testing} ...")
    backtester = BacktestEngine(start_date=params.get("start_date"),
                                end_date=params.get("end_date"),
                                sell_strike_method=params.get("sell_strike_method", "percent_under"),
                                portfolio_value=initial_portfolio_value,
                                spread=params.get("spread", 50))
    
    eval_data, unrealized_results = backtester.run()

    daily_returns = generate_daily_stats(unrealized_results, initial_portfolio_value)
    statistics = generate_portfolio_stats(daily_returns, initial_portfolio_value)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    backtester_results_dataset_id = os.getenv('backtester_results_dataset_id')
    backtester_results_table_name = f"{backtester_results_dataset_id}.unrealized_results_{timestamp}"

    backtester_daily_results_dataset_id = os.getenv('backtester_daily_results_dataset_id')
    backtester_daily_results_table_name = f"{backtester_daily_results_dataset_id}.daily_results_{timestamp}"

    backtest_upload_info = {
        backtester_results_table_name: {
            "dataframe": unrealized_results,
            "file_name": "unrealized_results.csv"
        },
        backtester_daily_results_table_name: {
            "dataframe": daily_returns,
            "file_name": "daily_results.csv"
        }
    }

    # Save unrealized_results to BigQuery and metadata to Postgres
    if testing:
        logger.info(f"Testing mode: skipping upload to BigQuery and Postgres")
        return {
            "task_id": task_id,
            "start_date": params.get("start_date"),
            "end_date": params.get("end_date"),
            "save_to_datastore": False,
            "statistics": statistics,
        }
    # Upload each results dataframe to BigQuery and upload metadata + statistics to Postgres
    for table_name, info in backtest_upload_info.items():
        upload_df_to_bigquery(table_name, info["dataframe"], info["file_name"])
        
    post_backtest_updates(task_id, backtest_id, backtester_daily_results_table_name, statistics)
    return {
            "task_id": task_id,
            "start_date": params.get("start_date"),
            "end_date": params.get("end_date"),
            "save_to_datastore": True,
            "statistics": statistics,
        }

def generate_daily_stats(unrealized_results, initial_portfolio_value):
    """
    Generate daily statistics based on unrealized results and initial portfolio value.

    Args:
        unrealized_results (DataFrame): DataFrame containing unrealized results.
        initial_portfolio_value (float): Initial portfolio value.

    Returns:
        DataFrame: DataFrame containing daily returns, portfolio value, and daily return percentage.
    """
    daily_returns = unrealized_results.groupby('current_date')['daily_trade_pnl'].sum().reset_index()
    daily_returns.columns = ['current_date', 'daily_return']
    daily_returns['portfolio_value'] = initial_portfolio_value + daily_returns['daily_return'].cumsum()
    daily_returns['daily_return_percent'] = daily_returns['portfolio_value'].pct_change() * 100
    return daily_returns

def generate_portfolio_stats(daily_returns, initial_portfolio_value):
    """
    Calculate various statistics for a portfolio based on daily returns.

    Args:
        daily_returns (DataFrame): DataFrame containing daily returns.
        initial_portfolio_value (float): Initial value of the portfolio.

    Returns:
        dict: A dictionary containing the following statistics:
            - total_return_percentage (float): Total return percentage.
            - total_return (float): Total return value.
            - max_drawdown_percent (float): Maximum drawdown percentage.
            - max_drawdown (float): Maximum drawdown value.
            - std_deviation (float): Standard deviation of daily returns.
            - positive_periods (int): Number of positive return periods.
            - negative_periods (int): Number of negative return periods.
            - average_daily_return (float): Average daily return percentage.
    """
    # Total Percentage Return
    total_return_percentage, total_return = calculate_total_return(daily_returns, initial_portfolio_value)

    # Max Drawdown
    max_drawdown_percent, max_drawdown = calculate_max_drawdown(daily_returns, initial_portfolio_value)

    # Standard Deviation
    std_deviation = calculate_portfolio_std(daily_returns)

    positive_periods = int((daily_returns['daily_return_percent'] > 0).sum())
    negative_periods = int((daily_returns['daily_return_percent'] < 0).sum())

    average_daily_return = daily_returns['daily_return_percent'].mean()

    return {
        'total_return_percentage': total_return_percentage,
        'total_return': total_return,
        'max_drawdown_percent': max_drawdown_percent,
        'max_drawdown': max_drawdown,
        'std_deviation': std_deviation,
        'positive_periods': positive_periods,
        'negative_periods': negative_periods,
        'average_daily_return': average_daily_return
    }

def upload_df_to_bigquery(table_name, df, file_name):
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

def post_backtest_updates(task_id, backtest_id, backtest_table_name, statistics):
    """
    Save the task to the Postgres backtests table and the statistics to a separate table.

    Args:
        task_id (str): The ID of the task.
        backtest_table_name (str): The name of the table in Postgres to save the backtest information.
        statistics (dict): The statistics to be saved.

    Raises:
        Exception: If there is an error while saving the task or statistics to Postgres.

    """
    session = Session()
    try:
        # Update the row with bigquery_table
        logger.info(f'Updating task {task_id} with BigQuery table name...')
        backtest = session.query(Backtest).filter(Backtest.id == backtest_id).first()
        backtest.bigquery_table = backtest_table_name
        backtest.status = 'completed'
        session.commit()

        logger.info(f'Saving statistics for task {task_id} to Postgres statistics table...')
        new_statistics = Statistic(id=uuid.uuid4(),
                                   backtest_id=backtest_id,
                                   **statistics)
        session.add(new_statistics)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f'Failed to save task {task_id} to Postgres: {e}')
        raise
    finally:
        session.close()

def error_status_update(backtest_id):
    """
    Updates the status column of a backtest to 'error'.

    Args:
        backtest_id (str): The ID of the backtest.
    """
    session = Session()
    try:
        logger.info(f'Updating backtest {backtest_id} status to error...')
        backtest = session.query(Backtest).filter(Backtest.id == backtest_id).first()
        backtest.status = 'error'
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f'Failed to update backtest {backtest_id} status to error: {e}')
        raise
    finally:
        session.close()