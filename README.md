# VASU

VASU is a Django-based fashion storefront with women's and men's catalogs, cart and checkout flows, account management, vendor/admin backoffice tools, and a product-search chatbot.

## Agile Documentation Period

- Start Date: 1 January 2026
- End Date: 20 April 2026
- Full Agile documentation: [AGILE_DOCUMENTATION.md](AGILE_DOCUMENTATION.md)

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

- The chatbot works even without Gemini enabled.
- Product search is handled locally from the catalog database.
- Gemini responses are optional and only used when `GEMINI_CHAT_ENABLED=True`, `GEMINI_API_KEY` is set, and `GEMINI_CHAT_MODEL` is configured.

## Deployment

### Render With Neon PostgreSQL

This project is configured for Neon PostgreSQL through `DATABASE_URL`. SQLite fallback is disabled, so local and production data writes go to the configured Postgres database.

Required Render environment variables:

- `DEBUG=False`
- `SECRET_KEY=<generated-by-render-or-strong-secret>`
- `DATABASE_URL=<your-neon-connection-string>`
- `DB_SSL_REQUIRE=True`
- `DB_CONN_MAX_AGE=600`
- `DB_CONN_HEALTH_CHECKS=True`
- `USE_HTTPS_SECURITY=True`
- `SERVE_MEDIA_FILES=True`
- `ALLOWED_HOSTS=.onrender.com,<your-custom-domain>`
- `CSRF_TRUSTED_ORIGINS=https://<your-custom-domain>` if you add a custom domain

Optional environment variables:

- `GEMINI_CHAT_ENABLED=False` unless you want AI-generated chatbot replies
- `GEMINI_API_KEY=<key>` only if AI replies are enabled
- `GEMINI_CHAT_MODEL=gemini-2.0-flash` only if AI replies are enabled
- `GOOGLE_OAUTH_CLIENT_ID=<google-client-id>` for Google OAuth login
- `GOOGLE_OAUTH_CLIENT_SECRET=<google-client-secret>` for Google OAuth login
- `SUPPORT_EMAIL=<support-inbox-email>` for contact and bug-report notifications
- `LOGIN_RATE_LIMIT_ATTEMPTS=5` failed logins before temporary lockout
- `LOGIN_RATE_LIMIT_WINDOW_SECONDS=900` counting window for failed logins
- `LOGIN_RATE_LIMIT_BLOCK_SECONDS=900` lockout duration after threshold
- `GOOGLE_SITE_VERIFICATION=<token-from-google-search-console>`
- `BING_SITE_VERIFICATION=<token-from-bing-webmaster-tools>`
- `SEO_SITE_NAME=VASU Store`
- `SEO_DEFAULT_DESCRIPTION=<your-brand-description>`

Google Cloud Console OAuth configuration:

Authorized JavaScript origins:

```text
http://localhost:8000
http://127.0.0.1:8000
https://vasu-dev.onrender.com
```

Authorized redirect URIs:

```text
http://localhost:8000/accounts/google/login/callback/
http://127.0.0.1:8000/accounts/google/login/callback/
https://vasu-dev.onrender.com/accounts/google/login/callback/
```

Render build command:

```bash
bash build.sh
```

Render pre-deploy command:

```bash
python manage.py migrate --noinput
```

Render start command:

```bash
gunicorn vasu.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-3} --log-file -
```

The build script installs dependencies and collects static files:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

Media files such as product images, review uploads, and profile pictures are served from Django at `/media/...` in both local development and Render production. The route is restricted to the app's upload directories (`photos/` and `userprofile/`) so it does not expose unrelated project files.

## Neon PostgreSQL as Primary Database

This project requires `DATABASE_URL`; there is no SQLite fallback. Put the Neon connection string in `.env` for local development and in your hosting provider's environment variables for production:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require&channel_binding=require
DB_SSL_REQUIRE=True
DB_CONN_MAX_AGE=600
DB_CONN_HEALTH_CHECKS=True
```

Run migrations against Neon:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Confirm Django is connected to Neon:

```powershell
.\.venv\Scripts\python.exe -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','vasu.settings'); import django; django.setup(); from django.db import connection; print(connection.vendor); print(connection.settings_dict['ENGINE'])"
```

Expected output:

```text
postgresql
django.db.backends.postgresql
```

## Move Data from SQLite to PostgreSQL

Use this only for the one-time SQLite-to-Neon copy. Do not run it again after production users have started creating data in Neon.

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

You can also store `DATABASE_URL` in `.env` or `.environment` and run the script without arguments:

```powershell
./scripts/migrate_sqlite_to_postgres.ps1
```

What this script does:

- Backs up `db.sqlite3`
- Exports SQLite data to `data/sqlite_to_postgres_dump.json`
- Runs migrations on PostgreSQL
- Loads the exported data into PostgreSQL
- Verifies row counts and stops if SQLite/PostgreSQL counts do not match

After migration, keep this in your `.env`:

- `DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DBNAME`

Useful deployment endpoint:

- `GET /health/` returns `{"status": "ok"}`

### Render Quick Deploy

This repository includes `render.yaml` for Blueprint deployment with an external Neon database.

1. Push this repository to GitHub.
2. In Render, choose **New +** -> **Blueprint**.
3. Select this repository and apply the blueprint.
4. Paste your Neon connection string into the `DATABASE_URL` environment variable.
5. Deploy. Render will run `bash build.sh`, then start Gunicorn.
6. For a custom domain, update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`, then redeploy.
7. If you expect users or admins to upload new files in production, do not stay on Render's free web service plan because local filesystem changes are ephemeral there. Move to a paid plan with a persistent disk or use object storage for media.

## Verification

```bash
python manage.py check
python manage.py test
```

## SEO and Search Submission

Built-in SEO endpoints:

- `/robots.txt`
- `/sitemap.xml`

Google Search Console submission:

1. Open Google Search Console and add your production domain as a Property.
2. Verify ownership using HTML tag method and set `GOOGLE_SITE_VERIFICATION` in `.env`.
3. Open **Sitemaps** in Search Console and submit `https://your-domain/sitemap.xml`.
4. Use **URL Inspection** for key pages (home, womens, mens, product pages) and request indexing.

Other search engines:

1. Bing Webmaster Tools: add the same site and verify with meta tag.
2. Set `BING_SITE_VERIFICATION` in `.env`.
3. Submit `https://your-domain/sitemap.xml` in Bing Webmaster Tools.
4. DuckDuckGo and Yahoo generally use Bing index data, so Bing submission covers them in practice.

SEO basics checklist:

- Canonical URL tags on key templates
- Meta description and robots directives
- Open Graph and Twitter card tags
- XML sitemap and robots.txt
- Noindex for sensitive pages like login/checkout
