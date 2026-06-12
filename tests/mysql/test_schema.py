"""Schema-level assertions against the real MySQL test DB.

These verify that ``Base.metadata.create_all`` produced exactly the
tables we expect, with the right charset / collation / engine, and that
key columns (LONGTEXT, AUTO_INCREMENT) ended up correct.

If any of these break, the SQLite-only dev path is masking a MySQL
incompatibility.
"""

from __future__ import annotations

EXPECTED_TABLES = {
    "users",
    "courses",
    "parse_tasks",
    "scripts",
    "audio_tasks",
    "lessons",
    "qa_sessions",
    "qa_records",
    "learning_progress",
    "adjust_records",
    "knowledge_bases",
    "knowledge_base_sources",
    "knowledge_chunks",
}


def test_all_expected_tables_created(raw_mysql_cursor, test_db_name):
    """The 13 tables defined in ``tables.py`` exist after init_db."""
    raw_mysql_cursor.execute(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
        (test_db_name,),
    )
    actual = {row[0] for row in raw_mysql_cursor.fetchall()}
    missing = EXPECTED_TABLES - actual
    extra = actual - EXPECTED_TABLES
    assert not missing, f"missing tables: {missing}"
    assert not extra, f"unexpected tables: {extra}"


def test_all_tables_use_innodb(raw_mysql_cursor, test_db_name):
    """Every table must be InnoDB so transactions / FK actually work."""
    raw_mysql_cursor.execute(
        "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
        (test_db_name,),
    )
    rows = raw_mysql_cursor.fetchall()
    non_innodb = [(t, e) for t, e in rows if e != "InnoDB"]
    assert not non_innodb, f"non-InnoDB tables: {non_innodb}"


def test_all_tables_use_utf8mb4(raw_mysql_cursor, test_db_name):
    """Charset must be utf8mb4 to support full CJK + emoji."""
    # MySQL 8/9 expose the table-level collation directly; we extract the
    # charset prefix from it (utf8mb4_unicode_ci → utf8mb4).
    raw_mysql_cursor.execute(
        "SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
        (test_db_name,),
    )
    bad = []
    for tn, collation in raw_mysql_cursor.fetchall():
        if not collation or not collation.startswith("utf8mb4"):
            bad.append((tn, collation))
    assert not bad, f"non-utf8mb4 tables: {bad}"


def test_longtext_columns_are_longtext(raw_mysql_cursor, test_db_name):
    """``parser_output`` / ``structured_content`` etc. must be LONGTEXT.

    Stored JSON often exceeds the 64KB TEXT cap on MySQL, so the schema
    must use LONGTEXT (``with_variant`` ensures SQLite still works).
    """
    expected_longtext = {
        ("parse_tasks", "structure_preview"),
        ("parse_tasks", "parser_output"),
        ("scripts", "script_structure"),
        ("scripts", "generate_output"),
        ("audio_tasks", "section_audios"),
        ("lessons", "structured_content"),
        ("lessons", "ppt_outline"),
        ("qa_records", "references_json"),
        ("knowledge_chunks", "text"),
    }

    raw_mysql_cursor.execute(
        "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND DATA_TYPE = 'longtext'",
        (test_db_name,),
    )
    actual = {(t, c) for t, c, _ in raw_mysql_cursor.fetchall()}

    # We assert the *important* columns are LONGTEXT.  The model file may
    # add more LONGTEXT fields over time; we only complain about regressions.
    missing = expected_longtext - actual
    assert not missing, (
        f"these columns were expected to be LONGTEXT but are not: {missing}. "
        "Did someone replace `LONGTEXT` with `Text` in tables.py?"
    )


def test_primary_keys_are_auto_increment(raw_mysql_cursor, test_db_name):
    """Every table has an AUTO_INCREMENT integer ``id`` PK."""
    raw_mysql_cursor.execute(
        """
        SELECT TABLE_NAME, COLUMN_NAME, EXTRA
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND COLUMN_KEY = 'PRI'
        """,
        (test_db_name,),
    )
    rows = raw_mysql_cursor.fetchall()
    by_table = {}
    for tn, cn, extra in rows:
        by_table.setdefault(tn, []).append((cn, extra))

    for table in EXPECTED_TABLES:
        cols = by_table.get(table, [])
        assert cols, f"{table} has no PK"
        # Expect a single ``id`` column with auto_increment.
        names = [c for c, _ in cols]
        extras = " ".join(e for _, e in cols)
        assert "id" in names, f"{table} PK is not on `id`: {names}"
        assert "auto_increment" in extras.lower(), f"{table}.id is not AUTO_INCREMENT (got extras={extras!r})"


def test_unique_constraints_exist(raw_mysql_cursor, test_db_name):
    """Identifier columns (parse_id, script_id, ...) must be UNIQUE."""
    expected_unique = {
        ("parse_tasks", "parse_id"),
        ("scripts", "script_id"),
        ("audio_tasks", "audio_id"),
        ("lessons", "lesson_id"),
        ("qa_sessions", "session_id"),
        ("qa_records", "answer_id"),
        ("learning_progress", "track_id"),
        ("adjust_records", "adjust_id"),
        ("knowledge_bases", "kb_id"),
        ("knowledge_base_sources", "kb_source_id"),
        ("users", "user_id"),
        ("courses", "course_id"),
    }

    raw_mysql_cursor.execute(
        """
        SELECT s.TABLE_NAME, s.COLUMN_NAME
        FROM information_schema.STATISTICS s
        WHERE s.TABLE_SCHEMA = %s
          AND s.NON_UNIQUE = 0
          AND s.INDEX_NAME != 'PRIMARY'
        """,
        (test_db_name,),
    )
    actual = {(t, c) for t, c in raw_mysql_cursor.fetchall()}
    missing = expected_unique - actual
    assert not missing, f"missing UNIQUE indexes: {missing}"


def test_timestamp_columns_have_defaults(raw_mysql_cursor, test_db_name):
    """``created_at`` defaults to CURRENT_TIMESTAMP, ``updated_at`` auto-updates."""
    raw_mysql_cursor.execute(
        """
        SELECT TABLE_NAME, COLUMN_NAME, COLUMN_DEFAULT, EXTRA
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND COLUMN_NAME IN ('created_at', 'updated_at')
        """,
        (test_db_name,),
    )
    rows = raw_mysql_cursor.fetchall()
    assert rows, "no created_at/updated_at columns found"
    for tn, cn, default, extra in rows:
        assert default is not None and "CURRENT_TIMESTAMP" in default.upper(), (
            f"{tn}.{cn} missing default CURRENT_TIMESTAMP (got {default!r})"
        )
        if cn == "updated_at":
            assert "on update" in extra.lower(), (
                f"{tn}.updated_at missing ON UPDATE clause (got extra={extra!r})"
            )


def test_can_insert_and_retrieve_chinese_emoji(db):
    """Smoke test for utf8mb4 round-trip."""
    from src.api.models.tables import Lesson

    lesson_id = "lesson_unicode_test"
    rec = Lesson(
        lesson_id=lesson_id,
        course_id="cou_unicode",
        lesson_name="第二节·力学初步 🚀💡",
        status="parsed",
        structured_content='{"emoji": "✨", "中文": "测试"}',
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    fetched = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    assert fetched.lesson_name == "第二节·力学初步 🚀💡"
    assert "✨" in fetched.structured_content

    # Cleanup so the next test doesn't see this row.
    db.delete(fetched)
    db.commit()
