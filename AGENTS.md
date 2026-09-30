# AGENTS.md — snowflake-warehouse-spend-circuit

**Company:** Snowflake
**Domain:** Enterprise Data Platform & Authority Governance

## Quick Rules
- **Test command:** `PYTHONPATH=src pytest tests/ -v`
- **Lint:** `ruff check src/ tests/`
- **No drive-by edits** — load the skill first.

## Architecture
- `src/snowflake_warehouse_spend_circuit/core.py` — Domain logic (Enterprise Data Platform & Authority Governance)
- `tests/` — Verified test suite
- `.github/workflows/ci.yml` — Enforced CI pipeline
