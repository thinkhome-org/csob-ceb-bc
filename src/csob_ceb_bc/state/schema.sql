PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS profiles (
    profile_key TEXT PRIMARY KEY,
    last_query_timestamp TEXT
);

CREATE TABLE IF NOT EXISTS download_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT,
    file_format TEXT,
    size INTEGER,
    status TEXT,
    url_hash TEXT,
    local_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS upload_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    size INTEGER,
    file_format TEXT,
    mode TEXT,
    status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS upload_rest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id TEXT NOT NULL REFERENCES upload_attempts(attempt_id),
    new_file_id TEXT,
    http_status INTEGER,
    json_status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS upload_finish_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id TEXT NOT NULL REFERENCES upload_attempts(attempt_id),
    finish_status TEXT,
    ticket_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS import_protocols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    new_file_id TEXT NOT NULL,
    upload_hash TEXT NOT NULL,
    filename TEXT,
    client_app_guid TEXT,
    local_path TEXT,
    downloaded_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    file_hash TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
