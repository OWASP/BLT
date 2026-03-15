"""
Tests for the Django-inspired ORM (src/libs/orm.py).

These tests focus on the query-building logic – they never hit a real database.
A lightweight async mock replaces the D1 database binding so that every
``await db.prepare(sql).bind(*params).all()`` call is intercepted and the
last executed SQL / parameters are captured for assertion.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from libs.orm import (
    QuerySet,
    Model,
    _validate_identifier,
    _convert_row,
    _convert_results,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

class _FakeStatement:
    """Mimics Cloudflare D1's prepared-statement object."""

    def __init__(self, db, sql):
        self._db = db
        self._sql = sql
        self._params = ()

    def bind(self, *params):
        self._params = params
        return self

    async def all(self):
        self._db._last_sql = self._sql
        self._db._last_params = self._params
        self._db._all_sql_calls.append(self._sql)
        return self._db._all_return

    async def first(self):
        self._db._last_sql = self._sql
        self._db._last_params = self._params
        self._db._all_sql_calls.append(self._sql)
        return self._db._first_return

    async def run(self):
        self._db._last_sql = self._sql
        self._db._last_params = self._params
        self._db._all_sql_calls.append(self._sql)


class MockDB:
    """Minimal async mock for a Cloudflare D1 database binding."""

    def __init__(self):
        self._last_sql = None
        self._last_params = None
        self._all_sql_calls: list = []  # all SQL statements executed
        # Default return values – tests may override these.
        self._all_return = _MockAllResult([])
        self._first_return = None

    def prepare(self, sql):
        return _FakeStatement(self, sql)


class _MockAllResult:
    """Simulates D1's ``all()`` result object."""

    def __init__(self, rows):
        self.results = rows


# A concrete model used throughout the tests.
class _TestModel(Model):
    table_name = "test_table"


# ---------------------------------------------------------------------------
# _validate_identifier
# ---------------------------------------------------------------------------


class TestValidateIdentifier:
    def test_simple_field(self):
        assert _validate_identifier("id") == "id"

    def test_field_with_underscores(self):
        assert _validate_identifier("user_id") == "user_id"

    def test_table_qualified(self):
        assert _validate_identifier("b.status") == "b.status"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _validate_identifier("")

    def test_space_raises(self):
        with pytest.raises(ValueError):
            _validate_identifier("user id")

    def test_semicolon_raises(self):
        with pytest.raises(ValueError):
            _validate_identifier("id; DROP TABLE users--")

    def test_dash_raises(self):
        with pytest.raises(ValueError):
            _validate_identifier("user-id")

    def test_dot_only_raises(self):
        with pytest.raises(ValueError):
            _validate_identifier(".")

    def test_double_dot_raises(self):
        with pytest.raises(ValueError):
            _validate_identifier("a..b")


# ---------------------------------------------------------------------------
# _convert_row / _convert_results
# ---------------------------------------------------------------------------


class TestConvertHelpers:
    def test_none_row(self):
        assert _convert_row(None) is None

    def test_dict_row(self):
        assert _convert_row({"id": 1}) == {"id": 1}

    def test_to_py_row(self):
        class Proxy:
            def to_py(self):
                return {"id": 99}

        assert _convert_row(Proxy()) == {"id": 99}

    def test_none_results(self):
        assert _convert_results(None) == []

    def test_list_results(self):
        rows = [{"id": 1}, {"id": 2}]
        assert _convert_results(rows) == rows

    def test_to_py_results(self):
        class Proxy:
            def to_py(self):
                return [{"id": 1}]

        assert _convert_results(Proxy()) == [{"id": 1}]


# ---------------------------------------------------------------------------
# QuerySet SQL generation
# ---------------------------------------------------------------------------


class TestQuerySetSQLGeneration:
    def setup_method(self):
        self.db = MockDB()
        self.qs = QuerySet(_TestModel, self.db)

    # --- filter / WHERE ---

    def test_no_filter(self):
        sql, params = self.qs._build_select_sql()
        assert sql == "SELECT * FROM test_table"
        assert params == []

    def test_filter_exact(self):
        sql, params = self.qs.filter(id=5)._build_select_sql()
        assert "WHERE id = ?" in sql
        assert params[0] == 5

    def test_filter_icontains(self):
        sql, params = self.qs.filter(name__icontains="test")._build_select_sql()
        assert "LOWER(name) LIKE LOWER(?)" in sql
        assert params[0] == "%test%"

    def test_filter_contains(self):
        sql, params = self.qs.filter(url__contains="example")._build_select_sql()
        assert "url LIKE ?" in sql
        assert params[0] == "%example%"

    def test_filter_startswith(self):
        sql, params = self.qs.filter(name__startswith="foo")._build_select_sql()
        assert "name LIKE ?" in sql
        assert params[0] == "foo%"

    def test_filter_endswith(self):
        sql, params = self.qs.filter(name__endswith="bar")._build_select_sql()
        assert "name LIKE ?" in sql
        assert params[0] == "%bar"

    def test_filter_gt(self):
        sql, params = self.qs.filter(score__gt=10)._build_select_sql()
        assert "score > ?" in sql
        assert params[0] == 10

    def test_filter_gte(self):
        sql, params = self.qs.filter(score__gte=10)._build_select_sql()
        assert "score >= ?" in sql

    def test_filter_lt(self):
        sql, params = self.qs.filter(score__lt=10)._build_select_sql()
        assert "score < ?" in sql

    def test_filter_lte(self):
        sql, params = self.qs.filter(score__lte=10)._build_select_sql()
        assert "score <= ?" in sql

    def test_filter_isnull_true(self):
        sql, params = self.qs.filter(closed_date__isnull=True)._build_select_sql()
        assert "closed_date IS NULL" in sql
        assert params == []

    def test_filter_isnull_false(self):
        sql, params = self.qs.filter(closed_date__isnull=False)._build_select_sql()
        assert "closed_date IS NOT NULL" in sql

    def test_filter_in(self):
        sql, params = self.qs.filter(status__in=["open", "closed"])._build_select_sql()
        assert "status IN (?, ?)" in sql
        assert "open" in params
        assert "closed" in params

    def test_filter_in_empty_list(self):
        sql, params = self.qs.filter(status__in=[])._build_select_sql()
        assert "1 = 0" in sql

    def test_exclude(self):
        sql, params = self.qs.exclude(is_hidden=1)._build_select_sql()
        assert "NOT (is_hidden = ?)" in sql
        assert params[0] == 1

    def test_multiple_filters_joined_with_and(self):
        sql, params = self.qs.filter(status="open", verified=1)._build_select_sql()
        assert "WHERE" in sql
        assert "AND" in sql

    # --- ORDER BY ---

    def test_order_by_asc(self):
        sql, _ = self.qs.order_by("created")._build_select_sql()
        assert "ORDER BY created ASC" in sql

    def test_order_by_desc(self):
        sql, _ = self.qs.order_by("-created")._build_select_sql()
        assert "ORDER BY created DESC" in sql

    def test_order_by_multiple(self):
        sql, _ = self.qs.order_by("-score", "id")._build_select_sql()
        assert "score DESC" in sql
        assert "id ASC" in sql

    # --- LIMIT / OFFSET ---

    def test_limit(self):
        sql, params = self.qs.limit(10)._build_select_sql()
        assert "LIMIT ?" in sql
        assert 10 in params

    def test_offset(self):
        sql, params = self.qs.limit(10).offset(20)._build_select_sql()
        assert "OFFSET ?" in sql
        assert 20 in params

    def test_paginate_page1(self):
        sql, params = self.qs.paginate(1, 20)._build_select_sql()
        assert "LIMIT ?" in sql
        assert 20 in params
        assert "OFFSET" not in sql  # offset 0 is omitted

    def test_paginate_page2(self):
        sql, params = self.qs.paginate(2, 20)._build_select_sql()
        assert "LIMIT ?" in sql
        assert "OFFSET ?" in sql
        assert 20 in params
        assert 20 in params  # offset = (2-1)*20 = 20

    def test_paginate_clamps_per_page(self):
        qs = self.qs.paginate(1, 9999)
        assert qs._limit_val == 100

    def test_limit_negative_raises(self):
        with pytest.raises(ValueError):
            self.qs.limit(-1)

    def test_limit_non_integer_raises(self):
        with pytest.raises(ValueError):
            self.qs.limit("10")  # type: ignore[arg-type]

    def test_offset_negative_raises(self):
        with pytest.raises(ValueError):
            self.qs.offset(-5)

    def test_offset_non_integer_raises(self):
        with pytest.raises(ValueError):
            self.qs.offset(3.5)  # type: ignore[arg-type]

    # --- VALUES (SELECT specific fields) ---

    def test_values(self):
        sql, _ = self.qs.values("id", "name")._build_select_sql()
        assert "SELECT id, name FROM test_table" in sql

    # --- Chaining is immutable ---

    def test_chaining_does_not_mutate_original(self):
        original = self.qs
        filtered = original.filter(id=1)
        assert original._filters == []
        assert len(filtered._filters) == 1


# ---------------------------------------------------------------------------
# Security: unsafe field names must be rejected
# ---------------------------------------------------------------------------


class TestSQLInjectionPrevention:
    def setup_method(self):
        self.db = MockDB()
        self.qs = QuerySet(_TestModel, self.db)

    def test_filter_with_unsafe_field_name(self):
        with pytest.raises(ValueError):
            self.qs.filter(**{"id; DROP TABLE users--": 1})

    def test_filter_with_space_in_field(self):
        with pytest.raises(ValueError):
            self.qs.filter(**{"user id": 1})

    def test_order_by_unsafe_field(self):
        with pytest.raises(ValueError):
            self.qs.order_by("created; DROP TABLE users--")

    def test_order_by_unsafe_desc(self):
        with pytest.raises(ValueError):
            self.qs.order_by("-created; DROP TABLE users--")

    def test_values_unsafe_field(self):
        with pytest.raises(ValueError):
            self.qs.values("id", "name; DROP TABLE users--")

    def test_exclude_unsafe_field(self):
        with pytest.raises(ValueError):
            self.qs.exclude(**{"is_hidden; --": 0})

    @pytest.mark.asyncio
    async def test_update_unsafe_field(self):
        """update() must reject unsafe field names."""
        with pytest.raises(ValueError):
            await self.qs.update(**{"is_active; DROP TABLE users--": 1})

    def test_unsafe_value_does_not_break_parameterization(self):
        """Malicious values are passed as bound params – SQL must not contain them."""
        evil = "'; DROP TABLE users; --"
        sql, params = self.qs.filter(name=evil)._build_select_sql()
        assert evil not in sql
        assert evil in params


# ---------------------------------------------------------------------------
# Async executor methods
# ---------------------------------------------------------------------------


class TestQuerySetAsyncMethods:
    def setup_method(self):
        self.db = MockDB()
        self.qs = QuerySet(_TestModel, self.db)

    @pytest.mark.asyncio
    async def test_all_returns_list(self):
        self.db._all_return = _MockAllResult([{"id": 1}, {"id": 2}])
        rows = await self.qs.all()
        assert rows == [{"id": 1}, {"id": 2}]

    @pytest.mark.asyncio
    async def test_first_returns_dict(self):
        self.db._first_return = {"id": 42}
        row = await self.qs.first()
        assert row == {"id": 42}

    @pytest.mark.asyncio
    async def test_first_returns_none_when_empty(self):
        self.db._first_return = None
        row = await self.qs.first()
        assert row is None

    @pytest.mark.asyncio
    async def test_get_returns_matching_row(self):
        self.db._first_return = {"id": 7}
        row = await self.qs.get(id=7)
        assert row == {"id": 7}
        assert "WHERE id = ?" in self.db._last_sql
        assert 7 in self.db._last_params

    @pytest.mark.asyncio
    async def test_count_returns_int(self):
        self.db._first_return = {"total": 15}
        n = await self.qs.count()
        assert n == 15

    @pytest.mark.asyncio
    async def test_count_with_filter(self):
        self.db._first_return = {"total": 3}
        n = await self.qs.filter(status="open").count()
        assert n == 3
        assert "WHERE status = ?" in self.db._last_sql
        assert "open" in self.db._last_params

    @pytest.mark.asyncio
    async def test_exists_true(self):
        self.db._first_return = {"total": 1}
        assert await self.qs.exists() is True

    @pytest.mark.asyncio
    async def test_exists_false(self):
        self.db._first_return = {"total": 0}
        assert await self.qs.exists() is False

    @pytest.mark.asyncio
    async def test_update_builds_correct_sql(self):
        await self.qs.filter(id=1).update(is_active=True)
        assert "UPDATE test_table SET is_active = ?" in self.db._last_sql
        assert "WHERE id = ?" in self.db._last_sql
        assert True in self.db._last_params
        assert 1 in self.db._last_params

    @pytest.mark.asyncio
    async def test_delete_builds_correct_sql(self):
        await self.qs.filter(id=5).delete()
        assert "DELETE FROM test_table" in self.db._last_sql
        assert "WHERE id = ?" in self.db._last_sql
        assert 5 in self.db._last_params


# ---------------------------------------------------------------------------
# Model.create
# ---------------------------------------------------------------------------


class TestModelCreate:
    @pytest.mark.asyncio
    async def test_create_raises_on_empty_kwargs(self):
        db = MockDB()
        with pytest.raises(ValueError):
            await _TestModel.create(db)

    @pytest.mark.asyncio
    async def test_create_builds_insert_sql(self):
        db = MockDB()
        db._first_return = {"id": 1}
        await _TestModel.create(db, name="test")
        # create() executes INSERT then SELECT; check INSERT was called
        assert any("INSERT INTO test_table" in s for s in db._all_sql_calls)

    @pytest.mark.asyncio
    async def test_create_rejects_unsafe_field_name(self):
        db = MockDB()
        with pytest.raises(ValueError):
            await _TestModel.create(db, **{"name; DROP TABLE test_table--": "evil"})


# ---------------------------------------------------------------------------
# Model.update_by_id
# ---------------------------------------------------------------------------


class TestModelUpdateById:
    @pytest.mark.asyncio
    async def test_update_by_id(self):
        db = MockDB()
        await _TestModel.update_by_id(db, 42, is_active=False)
        assert "UPDATE test_table" in db._last_sql
        assert "WHERE id = ?" in db._last_sql


# ---------------------------------------------------------------------------
# QuerySet.join — SQL generation and validation
# ---------------------------------------------------------------------------


class TestJoin:
    def setup_method(self):
        self.db = MockDB()
        self.qs = QuerySet(_TestModel, self.db)

    def test_join_generates_correct_sql(self):
        sql, _ = self.qs.join(
            "domains", on="bugs.domain_id = domains.id", join_type="LEFT"
        )._build_select_sql()
        assert "LEFT JOIN domains ON bugs.domain_id = domains.id" in sql

    def test_inner_join_default(self):
        sql, _ = self.qs.join(
            "domains", on="bugs.domain_id = domains.id"
        )._build_select_sql()
        assert "INNER JOIN domains ON bugs.domain_id = domains.id" in sql

    def test_join_invalid_type_raises(self):
        with pytest.raises(ValueError):
            self.qs.join(
                "domains", on="bugs.domain_id = domains.id", join_type="CROSS"
            )

    def test_join_unsafe_table_name_raises(self):
        with pytest.raises(ValueError):
            self.qs.join(
                "domains; DROP TABLE bugs--",
                on="bugs.domain_id = domains.id"
            )

    def test_join_unsafe_on_lhs_raises(self):
        with pytest.raises(ValueError):
            self.qs.join(
                "domains",
                on="bugs.domain_id; DROP TABLE bugs-- = domains.id"
            )

    def test_join_unsafe_on_rhs_raises(self):
        with pytest.raises(ValueError):
            self.qs.join(
                "domains",
                on="bugs.domain_id = domains.id; DROP TABLE bugs--"
            )

    def test_join_on_clause_canonical_form_stored(self):
        """Whitespace-folding bypass prevention — canonical ON clause is stored."""
        qs = self.qs.join(
            "domains",
            on="bugs.domain_id = domains.id"
        )
        _, join_table, on_clause = qs._joins[0]
        assert on_clause == "bugs.domain_id = domains.id"
        assert "  " not in on_clause

    def test_join_on_clause_whitespace_folding_bypass_rejected(self):
        """Extra whitespace cannot be used to smuggle unsafe expressions."""
        with pytest.raises(ValueError):
            self.qs.join(
                "domains",
                on="bugs.domain_id = domains.id OR 1"
            )

    def test_join_on_clause_without_equals_raises(self):
        with pytest.raises(ValueError):
            self.qs.join("domains", on="bugs.domain_id")

    def test_join_does_not_mutate_original(self):
        original = self.qs
        joined = original.join("domains", on="bugs.domain_id = domains.id")
        assert original._joins == []
        assert len(joined._joins) == 1

    def test_multiple_joins_chained(self):
        sql, _ = self.qs            .join("domains", on="bugs.domain_id = domains.id", join_type="LEFT")            .join("tags", on="bugs.tag_id = tags.id", join_type="INNER")            ._build_select_sql()
        assert "LEFT JOIN domains ON bugs.domain_id = domains.id" in sql
        assert "INNER JOIN tags ON bugs.tag_id = tags.id" in sql

    def test_join_placed_before_where(self):
        sql, _ = self.qs            .join("domains", on="bugs.domain_id = domains.id", join_type="LEFT")            .filter(id=1)            ._build_select_sql()
        join_pos = sql.index("LEFT JOIN")
        where_pos = sql.index("WHERE")
        assert join_pos < where_pos

    @pytest.mark.asyncio
    async def test_count_with_join_includes_join_clause(self):
        self.db._first_return = {"total": 5}
        await self.qs.join(
            "domains", on="bugs.domain_id = domains.id", join_type="LEFT"
        ).count()
        assert "LEFT JOIN domains ON bugs.domain_id = domains.id" in self.db._last_sql
        assert "COUNT(*)" in self.db._last_sql

    @pytest.mark.asyncio
    async def test_count_without_join_excludes_join_clause(self):
        self.db._first_return = {"total": 3}
        await self.qs.filter(id=1).count()
        assert "JOIN" not in self.db._last_sql


# ---------------------------------------------------------------------------
# QuerySet.update and delete — JOIN guards
# ---------------------------------------------------------------------------


class TestUpdateDeleteJoinGuards:
    def setup_method(self):
        self.db = MockDB()
        self.qs = QuerySet(_TestModel, self.db)

    @pytest.mark.asyncio
    async def test_update_with_join_raises(self):
        with pytest.raises(ValueError, match=r"update() is not supported"):
            await self.qs.join(
                "domains", on="bugs.domain_id = domains.id"
            ).update(status="open")

    @pytest.mark.asyncio
    async def test_delete_with_join_raises(self):
        with pytest.raises(ValueError, match=r"delete() is not supported"):
            await self.qs.join(
                "domains", on="bugs.domain_id = domains.id"
            ).delete()

    @pytest.mark.asyncio
    async def test_update_without_join_works(self):
        await self.qs.filter(id=1).update(status="open")
        assert "UPDATE test_table" in self.db._last_sql

    @pytest.mark.asyncio
    async def test_delete_without_join_works(self):
        await self.qs.filter(id=1).delete()
        assert "DELETE FROM test_table" in self.db._last_sql
