"""Data SQL generators: DDL (CREATE TABLE) + SEED (INSERT/upsert) + assemble.

Phase 6 / Task 1.  Both DDL and SEED go into one file at the path given by
``contract["bindings"]["paths"]["db_init_sql"]`` (default ``db/init.sql``).

Public API
----------
pgm_url_from_vue_page(vue_page) -> str
gen_ddl(contract, guide)        -> Coroutine[str]   (SQL string, no fences)
gen_seed(contract, guide)       -> Coroutine[str]   (SQL string, no fences)
assemble_sql(contract, ddl, seed) -> dict[str, str]  {path: combined_sql}
"""

from __future__ import annotations

import json

from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import GENERATOR_SYSTEM
from app.llm.graph._text import strip_fences as _strip_fences


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def pgm_url_from_vue_page(vue_page: str) -> str:
    """Derive a slash-separated, no-leading-slash pgm_url from a vue_page path.

    Examples
    --------
    ``src/pages/edu/pondg/x/index.vue`` → ``pages/edu/pondg/x/index.vue``
    ``pages/edu/x/index.vue``           → ``pages/edu/x/index.vue``  (idempotent)
    """
    # normalise backslashes (Windows paths)
    path = vue_page.replace("\\", "/")
    # strip leading "src/" prefix if present
    if path.startswith("src/"):
        path = path[len("src/"):]
    # guarantee no leading slash (belt-and-suspenders)
    path = path.lstrip("/")
    return path


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

async def gen_ddl(contract: dict, guide: str) -> str:
    """Generate a CREATE TABLE DDL for the contract's primary table.

    The prompt grounds the model in the actual table name and column list from
    the contract, plus the provided guide text.  PostgreSQL-specific rules are
    embedded so the model produces compliant output:

    * PK column typed BIGSERIAL (auto-increment)
    * del_yn CHAR(1) NOT NULL DEFAULT 'N' (soft-delete flag)
    * Audit columns: insert_uid, insert_dt (timestamptz), update_uid, update_dt
    * Do NOT store *_nm columns in the table — JOIN at SELECT time instead
    """
    table = contract["table"]
    table_name = table["name"]
    columns_json = json.dumps(table["columns"], ensure_ascii=False)
    pk_cols = ", ".join(table.get("pk", []))

    user = f"""\
{guide}

## Target table
Table name : {table_name}
Primary key: {pk_cols}
Columns (from contract):
{columns_json}

## PostgreSQL DDL rules (MUST follow)
1. PK column type: BIGSERIAL (auto-increment) — never SERIAL or BIGINT manually.
2. Add soft-delete column: del_yn CHAR(1) NOT NULL DEFAULT 'N'.
3. Add audit columns: insert_uid VARCHAR(50), insert_dt timestamptz DEFAULT now(),
   update_uid VARCHAR(50), update_dt timestamptz DEFAULT now().
4. Do NOT store *_nm columns in the table — retrieve them via JOIN at SELECT time.
5. All NOT NULL constraints must be explicit.
6. Output ONLY the CREATE TABLE statement (no comments, no DROP IF EXISTS).
"""
    reply = await gpt55_client.complete(GENERATOR_SYSTEM, user)
    return _strip_fences(reply)


async def gen_seed(contract: dict, guide: str) -> str:
    """Generate seed INSERT/upsert statements for CPMS metadata tables.

    Derives ``pgm_url`` deterministically from
    ``contract["bindings"]["paths"]["vue_page"]`` so it is never the old
    leading-slash form.

    Seed table insertion order (MERGE 금지 — use INSERT … ON CONFLICT):
    1. cmn_mnu  (menu registration)
    2. cmn_pgm  (program / screen registration, uses pgm_url)
    3. cmn_mnu_pgm  (menu ↔ program mapping)
    4. cmn_pgm_lbl  (field labels)
    """
    # Derive pgm_url without leading slash
    pgm_url = pgm_url_from_vue_page(contract["bindings"]["paths"]["vue_page"])

    identity = contract["identity"]
    program_id = identity["program_id"]
    seed_data = dict(contract["seed"])
    # Overwrite pgm_url in the copy fed to the model (contract may carry "")
    seed_data["pgm_url"] = pgm_url

    seed_json = json.dumps(seed_data, ensure_ascii=False)

    user = f"""\
{guide}

## Target screen
program_id : {program_id}
pgm_url    : {pgm_url}

## Seed data (from contract)
{seed_json}

## Seed generation rules (MUST follow)
1. Table insertion order: cmn_mnu → cmn_pgm → cmn_mnu_pgm → cmn_pgm_lbl.
2. Use INSERT … ON CONFLICT (DO UPDATE SET …) for every row — MERGE 금지.
3. pgm_url in cmn_pgm must be exactly: {pgm_url}  (no leading slash, no "src/" prefix).
4. Use the exact program_id: {program_id}.
5. Output ONLY the INSERT statements, no DDL, no comments beyond inline ones.
"""
    reply = await gpt55_client.complete(GENERATOR_SYSTEM, user)
    return _strip_fences(reply)


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------

def assemble_sql(contract: dict, ddl: str, seed: str) -> dict[str, str]:
    """Concatenate DDL then SEED into the single init SQL file.

    Returns ``{path: combined_sql}`` where *path* comes from
    ``contract["bindings"]["paths"]["db_init_sql"]`` (default ``db/init.sql``).
    DDL always precedes SEED in the output.
    """
    path = contract["bindings"]["paths"].get("db_init_sql", "db/init.sql")
    combined = ddl.rstrip() + "\n\n" + seed.lstrip()
    return {path: combined}
