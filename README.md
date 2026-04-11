# VASU

VASU is a Django-based fashion storefront with women's and men's catalogs, cart and checkout flows, account management, vendor/admin backoffice tools, and a product-search chatbot.

## Local Setup

1. Create and activate the virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` from `.env.example` and fill in the values you need.
4. Run migrations:

```bash
python manage.py migrate
```

5. Start the development server:

```bash
python manage.py runserver
```

## Chatbot

- The chatbot works even without OpenAI enabled.
- Product search is handled locally from the catalog database.
- OpenAI responses are optional and only used when `OPENAI_CHAT_ENABLED=True`, `OPENAI_API_KEY` is set, and `OPENAI_CHAT_MODEL` is configured.

## Deployment

Recommended environment variables:

- `DEBUG=False`
- `SECRET_KEY=<strong-secret-key>`
- `ALLOWED_HOSTS=<your-domain>`
- `CSRF_TRUSTED_ORIGINS=https://<your-domain>`
- `DATABASE_URL=<managed-database-url>` for PostgreSQL or another supported database
- `USE_HTTPS_SECURITY=True`
- `OPENAI_CHAT_ENABLED=False` unless you want AI-generated chatbot replies
- `OPENAI_API_KEY=<key>` only if AI replies are enabled
- `OPENAI_CHAT_MODEL=<model-name>` only if AI replies are enabled

Build and release steps:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn vasu.wsgi
```

## Move Data from SQLite to PostgreSQL

Prerequisites:

- Create a PostgreSQL database and get its URL in this format:
	`postgres://USER:PASSWORD@HOST:PORT/DBNAME`
- Install dependencies:

```bash
pip install -r requirements.txt
```

Automated migration script (PowerShell on Windows):

```powershell
./scripts/migrate_sqlite_to_postgres.ps1 -PostgresUrl "postgres://USER:PASSWORD@HOST:PORT/DBNAME"
```

What this script does:

- Backs up `db.sqlite3`
- Exports SQLite data to `data/sqlite_to_postgres_dump.json`
- Runs migrations on PostgreSQL
- Loads the exported data into PostgreSQL

After migration, keep this in your `.env`:

- `DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DBNAME`

Useful deployment endpoint:

- `GET /health/` returns `{"status": "ok"}`

### Render Quick Deploy

This repository includes `render.yaml` for Blueprint deployment.

1. Push this repository to GitHub.
2. In Render, choose **New +** -> **Blueprint**.
3. Select this repository and apply the blueprint.
4. After the first deploy, update these env values in Render:
	- `ALLOWED_HOSTS`
	- `CSRF_TRUSTED_ORIGINS`
5. Re-deploy after updating your actual domain.

## Verification

```bash
python manage.py check
python manage.py test
```
