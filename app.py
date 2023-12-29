import os
import uuid
import logging
from flask import Flask, request, jsonify
from tasks import run_backtest
from functools import wraps
from database.db import Session
from database.models import Backtest


logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
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

@app.route('/backtest_status/<task_id>', methods=['GET'])
@require_api_key
def backtest_status(task_id):
    # Query the status of the backtest task
    task = run_backtest.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'result': task.info,  # this is the result returned by `run_backtest` task
        }
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)

def pre_backtest_updates(task_id, params):
    session = Session()
    try:
        logging.info(f'Saving task {task_id} to Postgres backtests table...')
        
        new_backtest = Backtest(id=params['backtest_id'],
                                task_id=task_id,
                                start_date=params['start_date'],
                                end_date=params['end_date'],
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
