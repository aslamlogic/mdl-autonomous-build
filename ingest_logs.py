#!/usr/bin/env python3
"""
ingest_logs.py

Idempotently import logs/errors.log and logs/solutions.log (JSONL) into SQLite,
and export full NDJSON/CSV manifests for downstream data-science workflows.

Default files:
  - logs/errors.log
  - logs/solutions.log
Outputs:
  - errors_solutions.db (SQLite)
  - exports/incidents_export.ndjson
  - exports/solutions_export.ndjson
  - exports/solution_incidents.csv

No external dependencies.
"""
import os
import sys
import json
import sqlite3
import hashlib
import csv
from datetime import datetime
from typing import Any, Dict

DB_FILE = os.environ.get("INGEST_DB", "errors_solutions.db")
LOG_DIR = os.environ.get("INGEST_LOG_DIR", "logs")
ERRORS_FILE = os.path.join(LOG_DIR, "errors.log")
SOLUTIONS_FILE = os.path.join(LOG_DIR, "solutions.log")
EXPORT_DIR = os.environ.get("INGEST_EXPORT_DIR", "exports")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

def sha256_of_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def normalize_incident(obj: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure expected fields, keep raw json
    incident_id = obj.get("incident_id") or obj.get("id") or ("inc-" + sha256_of_text(json.dumps(obj, sort_keys=True))[:16])
    timestamp = obj.get("timestamp") or obj.get("recorded_at") or obj.get("created_at") or datetime.utcnow().isoformat() + "Z"
    message = obj.get("message") or ""
    stack = obj.get("stacktrace") or obj.get("stack") or ""
    component = obj.get("component") or ""
    run_command = obj.get("run_command") or obj.get("run") or None
    severity = obj.get("severity") or "medium"
    commit = obj.get("env_commit") or obj.get("commit_id") or None
    render_build = obj.get("env_render_build") or obj.get("render_build_id") or None
    signature = obj.get("signature") or (sha256_of_text((component + "|" + message + "|" + (stack or "") ) ) )
    return {
        "incident_id": incident_id,
        "timestamp": timestamp,
        "signature": signature,
        "component": component,
        "message": message,
        "stacktrace": stack,
        "run_command_json": json.dumps(run_command, ensure_ascii=False) if run_command is not None else None,
        "severity": severity,
        "commit_id": commit,
        "render_build_id": render_build,
        "raw_json": json.dumps(obj, ensure_ascii=False),
    }

def normalize_solution(obj: Dict[str, Any]) -> Dict[str, Any]:
    solution_id = obj.get("solution_id") or obj.get("id") or ("sol-" + sha256_of_text(json.dumps(obj, sort_keys=True))[:16])
    recorded_at = obj.get("recorded_at") or obj.get("timestamp") or datetime.utcnow().isoformat() + "Z"
    patch_summary = obj.get("patch_summary") or obj.get("summary") or ""
    branch = obj.get("branch") or obj.get("branch_name") or None
    pr_url = obj.get("pr_url") or obj.get("pull_request") or None
    author = obj.get("author") or obj.get("invoked_by") or None
    test_results = obj.get("test_results") or obj.get("test_results_json") or obj.get("test_results") or None
    incident_ids = obj.get("incident_ids") or obj.get("incidents") or []
    # Normalize incident_ids into list of strings
    if isinstance(incident_ids, str):
        # try parse as JSON list or comma-separated
        try:
            parsed = json.loads(incident_ids)
            if isinstance(parsed, list):
                incident_ids = parsed
            else:
                incident_ids = [incident_ids]
        except Exception:
            incident_ids = [i.strip() for i in incident_ids.split(",") if i.strip()]
    if incident_ids is None:
        incident_ids = []
    return {
        "solution_id": solution_id,
        "recorded_at": recorded_at,
        "patch_summary": patch_summary,
        "branch": branch,
        "pr_url": pr_url,
        "author": author,
        "test_results_json": json.dumps(test_results, ensure_ascii=False) if test_results is not None else None,
        "incident_ids_list": json.dumps(incident_ids, ensure_ascii=False),
        "raw_json": json.dumps(obj, ensure_ascii=False),
    }

def create_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
      incident_id TEXT PRIMARY KEY,
      timestamp TEXT,
      signature TEXT,
      component TEXT,
      message TEXT,
      stacktrace TEXT,
      run_command_json TEXT,
      severity TEXT,
      commit_id TEXT,
      render_build_id TEXT,
      processed_flag INTEGER DEFAULT 0,
      raw_json TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS solutions (
      solution_id TEXT PRIMARY KEY,
      recorded_at TEXT,
      patch_summary TEXT,
      branch TEXT,
      pr_url TEXT,
      author TEXT,
      test_results_json TEXT,
      incident_ids_list TEXT,
      raw_json TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS solution_incidents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      solution_id TEXT,
      incident_id TEXT,
      UNIQUE(solution_id, incident_id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS meta_kv (
      k TEXT PRIMARY KEY,
      v TEXT
    );
    """)
    conn.commit()

def import_jsonl_to_db(conn: sqlite3.Connection, filepath: str, kind: str) -> int:
    """
    kind: "incident" or "solution"
    returns number of new inserts
    """
    if not os.path.isfile(filepath):
        print(f"[INFO] {kind} file not found: {filepath}")
        return 0
    inserted = 0
    cur = conn.cursor()
    with open(filepath, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                # skip bad line but record as synthetic incident
                print(f"[WARN] failed to parse line in {filepath}: {e}")
                continue
            if kind == "incident":
                rec = normalize_incident(obj)
                try:
                    cur.execute("""
                    INSERT OR IGNORE INTO incidents (incident_id,timestamp,signature,component,message,stacktrace,run_command_json,severity,commit_id,render_build_id,raw_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        rec["incident_id"],
                        rec["timestamp"],
                        rec["signature"],
                        rec["component"],
                        rec["message"],
                        rec["stacktrace"],
                        rec["run_command_json"],
                        rec["severity"],
                        rec["commit_id"],
                        rec["render_build_id"],
                        rec["raw_json"]
                    ))
                    if cur.rowcount:
                        inserted += 1
                except Exception as e:
                    print(f"[ERROR] DB insert incident failed: {e}")
            else:
                rec = normalize_solution(obj)
                try:
                    cur.execute("""
                    INSERT OR IGNORE INTO solutions (solution_id,recorded_at,patch_summary,branch,pr_url,author,test_results_json,incident_ids_list,raw_json)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """, (
                        rec["solution_id"],
                        rec["recorded_at"],
                        rec["patch_summary"],
                        rec["branch"],
                        rec["pr_url"],
                        rec["author"],
                        rec["test_results_json"],
                        rec["incident_ids_list"],
                        rec["raw_json"]
                    ))
                    if cur.rowcount:
                        inserted += 1
                    # also add mappings to solution_incidents table based on incident_ids_list
                    try:
                        incident_list = json.loads(rec["incident_ids_list"])
                        if isinstance(incident_list, list):
                            for iid in incident_list:
                                if not iid:
                                    continue
                                try:
                                    cur.execute("""
                                    INSERT OR IGNORE INTO solution_incidents (solution_id, incident_id) VALUES (?,?)
                                    """, (rec["solution_id"], str(iid)))
                                except Exception:
                                    pass
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[ERROR] DB insert solution failed: {e}")
    conn.commit()
    return inserted

def export_manifests(conn: sqlite3.Connection):
    # incidents NDJSON
    inc_out = os.path.join(EXPORT_DIR, "incidents_export.ndjson")
    sol_out = os.path.join(EXPORT_DIR, "solutions_export.ndjson")
    map_out = os.path.join(EXPORT_DIR, "solution_incidents.csv")
    with open(inc_out, "w", encoding="utf-8") as fh_inc, \
         open(sol_out, "w", encoding="utf-8") as fh_sol, \
         open(map_out, "w", encoding="utf-8", newline='') as fh_map:
        cur = conn.cursor()
        for row in cur.execute("SELECT raw_json FROM incidents ORDER BY timestamp ASC"):
            fh_inc.write(row[0] + "\n")
        for row in cur.execute("SELECT raw_json FROM solutions ORDER BY recorded_at ASC"):
            fh_sol.write(row[0] + "\n")
        writer = csv.writer(fh_map)
        writer.writerow(["solution_id","incident_id"])
        for row in cur.execute("SELECT solution_id,incident_id FROM solution_incidents ORDER BY solution_id"):
            writer.writerow([row[0], row[1]])
    print(f"[INFO] exported incidents -> {inc_out}")
    print(f"[INFO] exported solutions -> {sol_out}")
    print(f"[INFO] exported mappings -> {map_out}")

def summary(conn: sqlite3.Connection):
    cur = conn.cursor()
    tot_inc = cur.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    tot_sol = cur.execute("SELECT COUNT(*) FROM solutions").fetchone()[0]
    tot_map = cur.execute("SELECT COUNT(*) FROM solution_incidents").fetchone()[0]
    last_run = datetime.utcnow().isoformat() + "Z"
    print(f"[SUMMARY] incidents={tot_inc} solutions={tot_sol} mappings={tot_map} (DB: {DB_FILE})")
    cur.execute("INSERT OR REPLACE INTO meta_kv (k,v) VALUES (?,?)", ("last_ingest", last_run))
    conn.commit()

def main():
    conn = sqlite3.connect(DB_FILE)
    create_schema(conn)
    n_inc = import_jsonl_to_db(conn, ERRORS_FILE, "incident")
    n_sol = import_jsonl_to_db(conn, SOLUTIONS_FILE, "solution")
    if n_inc == 0 and n_sol == 0:
        print("[INFO] No new records imported.")
    else:
        print(f"[INFO] imported new incidents={n_inc}, new solutions={n_sol}")
    export_manifests(conn)
    summary(conn)
    conn.close()

if __name__ == "__main__":
    main()
