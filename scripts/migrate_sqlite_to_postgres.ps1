param(
    [Parameter(Mandatory = $true)]
    [string]$PostgresUrl,

    [string]$PythonExe = "d:\Education\VASU\env\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/6] Validating project paths..."
if (-not (Test-Path "manage.py")) {
    throw "Run this script from project root where manage.py exists."
}

if (-not (Test-Path "db.sqlite3")) {
    throw "db.sqlite3 not found in project root."
}

if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

$dumpFile = "data/sqlite_to_postgres_dump.json"

Write-Host "[2/6] Backing up current SQLite database..."
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "db.sqlite3" "data/db.sqlite3.backup_$timestamp"

Write-Host "[3/6] Exporting SQLite data..."
& $PythonExe manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission --indent 2 | Out-File -FilePath $dumpFile -Encoding utf8

Write-Host "[4/6] Installing/ensuring dependencies..."
& $PythonExe -m pip install -r requirements.txt

Write-Host "[5/6] Applying migrations on PostgreSQL..."
$env:DATABASE_URL = $PostgresUrl
$env:DEBUG = "False"
& $PythonExe manage.py migrate --noinput

Write-Host "[6/6] Importing data into PostgreSQL..."
& $PythonExe manage.py loaddata $dumpFile

Write-Host "Done. SQLite data copied to PostgreSQL successfully."
