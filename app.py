import os
import uuid
import logging
from flask_cors import CORS
from flask import Flask, request, jsonify
from tasks import run_backtest
from functools import wraps
from sqlalchemy import desc
from database.db import Session
from database.models import Backtest, Statistic
from utils import get_first_and_last_day
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY', "super-secret")

def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        api_key = os.getenv('x-api-key')
        
        received_api_key = request.headers.get('x-api-key')
        if received_api_key and received_api_key == api_key:
            logging.info('API key validated successfully.')
            return view_function(*args, **kwargs)
        else:
            logging.warning('API key is missing or incorrect.')
            return jsonify(error="API key is missing or incorrect"), 403
    return decorated_function

@app.route('/start_backtest', methods=['POST'])
@require_api_key
def start_backtest():
    try:
        # Extract parameters from the request
        params = request.get_json()
        # Add backtest_id to params
        backtest_id = uuid.uuid4()
        params['backtest_id'] = backtest_id
        # Start the backtest task
        task = run_backtest.delay(params)
        task_id = task.id
        # Save the initial backtesting info to Postgres
        pre_backtest_updates(task_id, params)
        # Return the task id to the client
        return jsonify({'task_id': task_id}), 202
    except Exception as e:
        return jsonify(error=str(e)), 400

@app.route('/backtests', methods=['GET'])
@require_api_key
def get_backtests():
    session = Session()
    try:
        # Perform a join between backtests and statistics tables and order by the submission date in descending order
        results = session.query(Backtest, Statistic)\
            .outerjoin(Statistic, Backtest.id == Statistic.backtest_id)\
            .order_by(desc(Backtest.submitted_at)).all()
        
        # Convert the query results to dictionaries and return as JSON
        backtests_statistics = [
            {
                'backtest': backtest.to_dict(),
                'statistic': statistic.to_dict() if statistic else None
            } for backtest, statistic in results
        ]
        return jsonify(backtests_statistics)
    
    except Exception as e:
        logging.error(f'Failed to fetch backtests: {e}')
        return jsonify(error=str(e)), 400
    finally:
        session.close()

@app.route('/raw_data', methods=['GET'])
@require_api_key
def get_raw_data():
    try:
        # Extract parameters from the query string
        bigquery_table = request.args.get('bigquery_table')
        logging.info(f"GET /raw_data for {bigquery_table}")

        # Create a BigQuery client
        client = bigquery.Client()

        # Query the table
        query = f"""
            SELECT tb.* 
            FROM `{bigquery_table}` tb
            ORDER BY tb.current_date ASC
            ;
        """

        query_job = client.query(query)
        results = query_job.result()
        results = [dict(row) for row in results]

        return jsonify(results)
    except Exception as e:
        return jsonify(error=str(e)), 400

def pre_backtest_updates(task_id, params):
    session = Session()
    try:
        logging.info(f'Saving task {task_id} to Postgres backtests table...')
        start_date, _ = get_first_and_last_day(params['start_date'])
        _, end_date = get_first_and_last_day(params['end_date'])
        new_backtest = Backtest(id=params['backtest_id'],
                                task_id=task_id,
                                start_date=start_date,
                                end_date=end_date,
                                spread=params.get('spread', 50),
                                initial_portfolio_value=params.get('initial_portfolio_value', 1000000),
                                status='running',
                                sell_strike_method=params.get('sell_strike_method', 'percent_under'))
        session.add(new_backtest)
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f'Failed to save task {task_id} to Postgres: {e}')
        raise
    finally:
        session.close()
