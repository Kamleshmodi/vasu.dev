param(
    [string]$PostgresUrl = "",

    [string]$PythonExe = "",

    [string]$PostgresHostAddr = "",

    [switch]$SkipDependencyInstall,

    [switch]$ResetPostgresData
)

$ErrorActionPreference = "Stop"

function Resolve-PythonExe {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        return $RequestedPath
    }

    $candidates = @(
        ".\.venv\Scripts\python.exe",
        ".\env\Scripts\python.exe",
        "python"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -eq "python") {
            $command = Get-Command python -ErrorAction SilentlyContinue
            if ($command) {
                return $command.Source
            }
            continue
        }

        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "Python executable not found. Pass -PythonExe explicitly."
}

function Normalize-PostgresUrl {
    param(
        [string]$Url,
        [string]$HostAddr
    )

    if (-not $HostAddr) {
        return $Url
    }

    if ($Url.Contains('?')) {
        return "$Url&hostaddr=$HostAddr"
    }

    return "$Url?hostaddr=$HostAddr"
}

function Get-DatabaseUrlFromFile {
    param(
        [string[]]$CandidateFiles = @(".env", ".environment")
    )

    foreach ($candidateFile in $CandidateFiles) {
        if (-not (Test-Path $candidateFile)) {
            continue
        }

        $line = Get-Content $candidateFile -ErrorAction SilentlyContinue |
            Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } |
            Select-Object -First 1

        if (-not $line) {
            continue
        }

        $value = ($line -split '=', 2)[1].Trim()
        if ($value.StartsWith('"') -and $value.EndsWith('"') -and $value.Length -ge 2) {
            return $value.Substring(1, $value.Length - 2)
        }

        return $value
    }

    return ""
}

function Get-TableCounts {
    param(
        [string]$DatabasePath,
        [string]$OutputPath,
        [string]$PythonPath
    )

    $script = @"
import json
import sqlite3
from pathlib import Path

db_path = Path(r"$DatabasePath")
output_path = Path(r"$OutputPath")
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
table_names = [row[0] for row in cur.fetchall()]
counts = {}
for table_name in table_names:
    cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    counts[table_name] = cur.fetchone()[0]
conn.close()
output_path.write_text(json.dumps(counts, indent=2), encoding='utf-8')
print(output_path)
"@

    $script | & $PythonPath -
}

function Invoke-Python {
    param(
        [string[]]$PyArgs,
        [string]$StepLabel
    )

    & $PythonExe @PyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "$StepLabel failed with exit code $LASTEXITCODE"
    }
}

Write-Host "[1/6] Validating project paths..."
if (-not (Test-Path "manage.py")) {
    throw "Run this script from project root where manage.py exists."
}

if (-not (Test-Path "db.sqlite3")) {
    throw "db.sqlite3 not found in project root."
}

$PythonExe = Resolve-PythonExe -RequestedPath $PythonExe
Write-Host "Using Python executable: $PythonExe"

$previousDatabaseUrl = $env:DATABASE_URL
$resolvedPostgresUrl = $PostgresUrl

if (-not $resolvedPostgresUrl) {
    $resolvedPostgresUrl = $previousDatabaseUrl
}

if (-not $resolvedPostgresUrl) {
    $resolvedPostgresUrl = Get-DatabaseUrlFromFile
}

if (-not $resolvedPostgresUrl) {
    throw "PostgreSQL URL missing. Pass -PostgresUrl or set DATABASE_URL in .env/.environment."
}

$effectivePostgresUrl = Normalize-PostgresUrl -Url $resolvedPostgresUrl -HostAddr $PostgresHostAddr

if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

$dumpFile = "data/sqlite_to_postgres_dump.json"
$sqliteCountFile = "data/sqlite_table_counts.json"
$postgresCountFile = "data/postgres_table_counts.json"

try {
    # Force SQLite for dump/export even if .env contains DATABASE_URL.
    $env:DATABASE_URL = ""

    Write-Host "[2/6] Backing up current SQLite database..."
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item "db.sqlite3" "data/db.sqlite3.backup_$timestamp"
    Get-TableCounts -DatabasePath "db.sqlite3" -OutputPath $sqliteCountFile -PythonPath $PythonExe | Out-Null

    Write-Host "[3/6] Exporting SQLite data..."
    $dumpScript = @"
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vasu.settings')
import django
from django.core.management import call_command

django.setup()

with open(r"$dumpFile", "w", encoding="utf-8") as output_file:
    call_command(
        'dumpdata',
        natural_foreign=True,
        natural_primary=True,
        indent=2,
        stdout=output_file,
    )
"@

    $dumpScript | & $PythonExe -
    if ($LASTEXITCODE -ne 0) {
        throw "SQLite export failed with exit code $LASTEXITCODE"
    }

    Write-Host "[4/6] Installing/ensuring dependencies..."
    if ($SkipDependencyInstall) {
        Write-Host "Skipping dependency installation as requested."
    }
    else {
        Invoke-Python -PyArgs @('-m', 'pip', 'install', '-r', 'requirements.txt') -StepLabel 'Dependency install'
    }

    Write-Host "[5/6] Applying migrations on PostgreSQL..."
    $env:DATABASE_URL = $effectivePostgresUrl
    Invoke-Python -PyArgs @('manage.py', 'migrate', '--noinput') -StepLabel 'PostgreSQL migrate'

    if ($ResetPostgresData) {
        Write-Host "ResetPostgresData enabled: flushing existing PostgreSQL data..."
        Invoke-Python -PyArgs @('manage.py', 'flush', '--noinput') -StepLabel 'PostgreSQL flush'
    }

    Write-Host "[6/6] Importing data into PostgreSQL..."
    Invoke-Python -PyArgs @('manage.py', 'loaddata', $dumpFile) -StepLabel 'PostgreSQL loaddata'
    Invoke-Python -PyArgs @('manage.py', 'check') -StepLabel 'Django check'

    $verificationScript = @"
import json
import os
from pathlib import Path
from django.db import connection
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vasu.settings')
django.setup()

sqlite_counts = json.loads(Path(r"$sqliteCountFile").read_text(encoding='utf-8'))
postgres_counts = {}

with connection.cursor() as cursor:
    for table_name in sqlite_counts.keys():
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            postgres_counts[table_name] = cursor.fetchone()[0]
        except Exception:
            postgres_counts[table_name] = None

comparison = {}
for table_name, sqlite_count in sqlite_counts.items():
    postgres_count = postgres_counts.get(table_name)
    comparison[table_name] = {
        'sqlite': sqlite_count,
        'postgres': postgres_count,
        'match': sqlite_count == postgres_count,
    }

Path(r"$postgresCountFile").write_text(json.dumps(postgres_counts, indent=2), encoding='utf-8')
Path(r"data/sqlite_postgres_count_diff.json").write_text(json.dumps(comparison, indent=2), encoding='utf-8')

mismatches = [
    f"{table_name}: sqlite={row_counts['sqlite']} postgres={row_counts['postgres']}"
    for table_name, row_counts in comparison.items()
    if not row_counts['match']
]

if mismatches:
    print("Count mismatches detected between SQLite and PostgreSQL:", flush=True)
    for mismatch in mismatches:
        print(mismatch, flush=True)
    raise SystemExit(1)

print(Path(r"$postgresCountFile"))
"@

    $verificationScript | & $PythonExe -
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL count verification failed with exit code $LASTEXITCODE"
    }

    Write-Host "Done. SQLite data copied to PostgreSQL successfully."
    Write-Host "SQLite counts saved to: $sqliteCountFile"
    Write-Host "PostgreSQL counts saved to: $postgresCountFile"
    Write-Host "Count comparison saved to: data/sqlite_postgres_count_diff.json"
}
finally {
    $env:DATABASE_URL = $previousDatabaseUrl
}
