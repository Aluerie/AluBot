# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Every SQL query in the bot's source has to prepare against a database built from the migrations.

PostgreSQL checks each query's tables, columns, functions and types without running it, so a typo or a missing
table or migration fails here instead of on prod. Queries built with f-strings can't be checked and are listed
in the failure message.

Runs only when ``SQL_CHECK_POSTGRES`` holds a connection string of a user who may create databases: CI sets it,
and at home LalaBot's dev-db container works (``postgresql://postgres:<password>@localhost:5433/postgres``).
"""

import asyncio
import os
from pathlib import Path

import pytest

from shared import sqlcheck

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get("SQL_CHECK_POSTGRES")


@pytest.mark.skipif(DSN is None, reason="SQL_CHECK_POSTGRES is not set")
def test_every_query_prepares() -> None:
    assert DSN is not None
    queries, fstrings = sqlcheck.find_queries(ROOT / "src")
    failures = asyncio.run(
        sqlcheck.prepare_all(
            DSN,
            queries,
            search_path="alubot",
            migration_dirs=[("alubot", ROOT / "migrations")],
            setup_sql=[(ROOT / "src" / "shared" / "scheduler" / "schema.sql").read_text(encoding="utf-8")],
        )
    )
    assert queries, "found no queries, so the search for them is broken"
    unchecked = "\n".join(f"  {query.location}" for query in fstrings) or "  (none)"
    report = "\n".join(f"{query.location}: {error}" for query, error in failures)
    assert not failures, f"{report}\n\nNot checked (f-strings):\n{unchecked}"
