# Franklin Planner (Portrait) – Flask + Render + Postgres

## Local setup (dev)
1) Create a local Postgres DB:
   - DB name: franklin_planner
   - user/pass: postgres/postgres (or set DATABASE_URL)

2) Create venv + install:
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   pip install -r requirements.txt

3) Migrations:
   export FLASK_APP=manage.py  (Windows: set FLASK_APP=manage.py)
   flask db init
   flask db migrate -m "init"
   flask db upgrade

4) Run:
   flask --app manage.py run --debug

Visit: http://127.0.0.1:5000

## Render deploy
- Create a new Render Blueprint and point it at this repo (uses render.yaml), OR:
  - Create Postgres in Render
  - Create Web Service
  - Set env var DATABASE_URL to Render's Postgres connection string
  - Start command: gunicorn wsgi:app

Note: Hosted Postgres often requires SSL. This app appends `sslmode=require` if missing.
