#!/usr/bin/env bash
set -euo pipefail

# 1. Create the Machine-Triggered Workflow
mkdir -p .github/workflows
cat > .github/workflows/autonomous_batch_audit.yml <<'YML'
name: Autonomous-Batch-Audit
on:
  schedule:
    - cron: '0 0 * * *'  # Triggered by the machine every night at midnight 
  push:
    paths:
      - 'logs/**'      # Triggered when new logs are pushed

jobs:
  batch-archive:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Ingestion Logic
        run: |
          python ingest_logs.py
          python scripts/provenance.py

      - name: Machine-Commit to Audit Branch
        run: |
          git config user.name "MDL-Factory-Bot"
          git config user.email "factory-bot@abacus.ai"
          # Create or switch to a dedicated audit branch
          git checkout -b audit-log || git checkout audit-log
          git add errors_solutions.db exports/
          git commit -m "autonomous: update audit records [$(date -u +%Y-%m-%d)]" || echo "No changes to audit."
          git push origin audit-log
YML

# 2. Finalize the Ingestor (ensure it is executable for the machine)
chmod +x ingest_logs.py
chmod +x scripts/provenance.py

# 3. Synchronize Initial State
git add .github/workflows/autonomous_batch_audit.yml
git commit -m "structural: implement autonomous batch auditing"
git push origin main

echo "AUTONOMOUS SYSTEM ONLINE."
echo "The machine is now scheduled to ingest and archive its own logs every 24 hours without human intervention."
