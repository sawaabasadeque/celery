<p><a target="_blank" href="https://app.eraser.io/workspace/3gqDvxUWy0i7b2QwokUH" id="edit-in-eraser-github-link"><img alt="Edit in Eraser" src="https://firebasestorage.googleapis.com/v0/b/second-petal-295822.appspot.com/o/images%2Fgithub%2FOpen%20in%20Eraser.svg?alt=media&amp;token=968381c8-a7e7-472a-8ed6-4a6626da5501"></a></p>

# Derivatives Backtesting Engine
## Overview
This repository contains the code of the cloud/devops infrastructure for a backtesting engine. The backtester simulates the trades of a specific multi-leg options strategy in Python using tabular options chain data stored in a data warehouse. Our infrastructure is based on Render and our data warehouse is built on Google's BigQuery.

## Software Architecture
![Backtester](/.eraser/3gqDvxUWy0i7b2QwokUH___sKBE7gxtknX4C1dnV5iZm5p6Y362___---figure---M3VarqTtxCKGK7XaGFeJM---figure---JMmCUZqRgfCqyyTacu1t5A.png "Backtester")

### Frontend
- The frontend is built with NextJS, React, TailwindCSS, Supabase and hosted as web service on Vercel. User authentication and management is handled by Clerk.
- Authenticated users to our site can send a POST request to start a new backtest with custom parameters and can send GET requests to retrieve previous backtests and its results.
### Render Infrastructure
- Our Flask application holds the endpoints to accept the GET and POST requests coming in from our frontend application. 
- If initializing a new backtest, the Flask app will delegate the long-running backtesting task to a Celery worker which communicates via our message broker Redis. 
- Once the worker completes the backtest, it will upload the results dataframe to BigQuery, our data warehouse and will upload the backtest's metadata and statistics to our PostgreSQL database.
![Render PostgreSQL Database](/.eraser/3gqDvxUWy0i7b2QwokUH___sKBE7gxtknX4C1dnV5iZm5p6Y362___---figure---PqZHZYumumJMdxsGaoApe---figure---YMLReHq3MlrbYQbYvwRmHg.png "Render PostgreSQL Database")

### Google Cloud Infrastructure
- GCP hosts our data warehouse, BigQuery.
- We store historical options chain data as a dataset on BigQuery. These tables are read in via the backtester to simulate trades on historical data. 
- Also, we upload backtesting results to a separate dataset, which can be accessed via our Flask app to serve on the frontend.
## Codebase
Our codebase is separated into three main sections: database/alembic, flask, backtesting source code. 

- The alembic directory hosts our database migrations and the database directory hosts our SQLAlchemy models for our PostgreSQL database. 
- Our Flask application hosts the main endpoints on the `app.py`  file while all Celery tasks are hosted on `tasks.py` .
- The backtester directory is a private submodule



<!--- Eraser file: https://app.eraser.io/workspace/3gqDvxUWy0i7b2QwokUH --->