import os
from flask import Flask, request, jsonify
from tasks import run_backtest
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', "super-secret")

def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        api_key = os.getenv('YOUR_API_KEY')
        if request.headers.get('x-api-key') and request.headers.get('x-api-key') == api_key:
            return view_function(*args, **kwargs)
        else:
            return jsonify(error="API key is missing or incorrect"), 403
    return decorated_function

# @app.route('/')
# def main():
#     return render_template('main.html')


# @app.route('/add', methods=['POST'])
# def add_inputs():
#     x = int(request.form['x'] or 0)
#     y = int(request.form['y'] or 0)
#     add.delay(x, y)
#     flash("Your addition job has been submitted.")
#     return redirect('/')

@app.route('/start_backtest', methods=['POST'])
@require_api_key
def start_backtest():
    # Extract parameters from the request
    params = request.get_json()
    # Start the backtest task
    task = run_backtest.delay(params)
    # Return the task id to the client
    return jsonify({'task_id': task.id}), 202

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
