from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from backend.config import settings
from backend.models import Signal

SCHEMA_VERSION = 3


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                macro_score REAL,
                macro_level INTEGER,
                total_candidates INTEGER DEFAULT 0,
                saved_signals INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                error TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                ticker TEXT NOT NULL,
                name TEXT,
                region TEXT,
                sector TEXT,
                asset_type TEXT,
                market TEXT,
                kuspit_status TEXT,
                thesis_type TEXT,
                level INTEGER,
                score_total REAL,
                score_technical REAL,
                score_macro REAL,
                score_sector REAL,
                score_data REAL,
                price REAL,
                support REAL,
                resistance REAL,
                stop REAL,
                target REAL,
                rr REAL,
                trend_score INTEGER,
                volume_score INTEGER,
                price_score INTEGER,
                momentum_score INTEGER,
                risk_score INTEGER,
                rsi REAL,
                ret5 REAL,
                ret20 REAL,
                data_quality TEXT,
                consensus_label TEXT,
                source_count INTEGER,
                source_valid_count INTEGER,
                source_divergence_pct REAL,
                data_sources_json TEXT,
                warnings_json TEXT,
                catalysts_json TEXT,
                verdict TEXT,
                ai_summary TEXT,
                outcome_status TEXT DEFAULT 'pending',
                outcome_note TEXT DEFAULT '',
                scan_run_id INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                signal_id INTEGER,
                ticker TEXT NOT NULL,
                source TEXT NOT NULL,
                price REAL,
                volume REAL,
                currency TEXT,
                timestamp TEXT,
                ok INTEGER,
                error TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_ticker_created ON signals(ticker, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_level_score ON signals(level, score_total)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_ticker_source ON source_snapshots(ticker, source)")
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )


def start_run() -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO scan_runs(started_at, status) VALUES(?, 'running')",
            (datetime.now().isoformat(timespec="seconds"),),
        )
        return int(cursor.lastrowid)


def finish_run(run_id: int, macro_score: float, macro_level: int, total: int, saved: int, error: str | None = None) -> None:
    status = "error" if error else "finished"
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE scan_runs
            SET finished_at=?, macro_score=?, macro_level=?, total_candidates=?, saved_signals=?, status=?, error=?
            WHERE id=?
            """,
            (datetime.now().isoformat(timespec="seconds"), macro_score, macro_level, total, saved, status, error, run_id),
        )


def insert_signal(signal: Signal, scan_run_id: int | None = None) -> int:
    data = signal.to_dict()
    data_sources = data.pop("data_sources")
    warnings = data.pop("warnings")
    catalysts = data.pop("catalysts")
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["data_sources_json"] = json.dumps(data_sources, ensure_ascii=False)
    data["warnings_json"] = json.dumps(warnings, ensure_ascii=False)
    data["catalysts_json"] = json.dumps(catalysts, ensure_ascii=False)
    data["scan_run_id"] = scan_run_id

    fields = list(data.keys())
    placeholders = ", ".join(["?"] * len(fields))
    sql = f"INSERT INTO signals({', '.join(fields)}) VALUES({placeholders})"

    with get_connection() as conn:
        cursor = conn.execute(sql, [data[field] for field in fields])
        signal_id = int(cursor.lastrowid)
        for snap in data_sources:
            conn.execute(
                """
                INSERT INTO source_snapshots(
                    created_at, signal_id, ticker, source, price, volume, currency, timestamp, ok, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["created_at"],
                    signal_id,
                    signal.ticker,
                    snap.get("source"),
                    snap.get("price"),
                    snap.get("volume"),
                    snap.get("currency"),
                    snap.get("timestamp"),
                    1 if snap.get("ok") else 0,
                    snap.get("error"),
                ),
            )
        return signal_id


def _row_to_signal(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["data_sources"] = json.loads(item.pop("data_sources_json") or "[]")
    item["warnings"] = json.loads(item.pop("warnings_json") or "[]")
    item["catalysts"] = json.loads(item.pop("catalysts_json") or "[]")
    return item


def list_signals(limit: int = 150, level: int | None = None, search: str = "") -> list[dict[str, Any]]:
    params: list[Any] = []
    clauses: list[str] = []
    if level is not None:
        clauses.append("level = ?")
        params.append(level)
    if search.strip():
        term = f"%{search.strip()}%"
        clauses.append(
            "(ticker LIKE ? OR name LIKE ? OR sector LIKE ? OR region LIKE ? OR thesis_type LIKE ?)"
        )
        params.extend([term] * 5)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM signals {where} ORDER BY id DESC LIMIT ?",
            params,
        ).fetchall()
    return [_row_to_signal(row) for row in rows]


def get_signal(signal_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM signals WHERE id=?", (signal_id,)).fetchone()
    return _row_to_signal(row) if row else None


def update_ai_summary(signal_id: int, ai_summary: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE signals SET ai_summary=? WHERE id=?", (ai_summary, signal_id))


def update_outcome(signal_id: int, status: str, note: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE signals SET outcome_status=?, outcome_note=? WHERE id=?",
            (status, note, signal_id),
        )


def summary() -> dict[str, Any]:
    with get_connection() as conn:
        latest_run = conn.execute("SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1").fetchone()
        counts = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN level=3 THEN 1 ELSE 0 END) AS level_3,
                SUM(CASE WHEN level=2 THEN 1 ELSE 0 END) AS level_2,
                SUM(CASE WHEN level=1 THEN 1 ELSE 0 END) AS level_1
            FROM signals
            """
        ).fetchone()
        quality_rows = conn.execute(
            "SELECT data_quality, COUNT(*) AS n FROM signals GROUP BY data_quality"
        ).fetchall()
    return {
        "total_signals": int(counts["total"] or 0),
        "level_3": int(counts["level_3"] or 0),
        "level_2": int(counts["level_2"] or 0),
        "level_1": int(counts["level_1"] or 0),
        "quality": {row["data_quality"]: int(row["n"]) for row in quality_rows},
        "latest_run": dict(latest_run) if latest_run else None,
    }
