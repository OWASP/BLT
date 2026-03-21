"""
Django-inspired ORM for Cloudflare D1 (SQLite) database.

Provides safe, parameterized query building with a familiar Django-like API.
All user-supplied values are passed as bound parameters to prevent SQL injection.
Field names are validated against an allowlist of safe characters before being
embedded in SQL, giving defence-in-depth beyond the parameterized values alone.

Usage example::

    from libs.orm import QuerySet
    from models import Domain, Bug, User

    # List active domains, newest first, page 2
    rows = await Domain.objects(db).filter(is_active=1).order_by('-created').paginate(2, 20).all()

    # Get a single domain by PK
    domain = await Domain.objects(db).get(id=42)

    # Count open bugs
    total = await Bug.objects(db).filter(status='open').count()

    # Create a new tag
    tag = await Tag.create(db, name='security')
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

T = TypeVar("T", bound="Model")

# ---------------------------------------------------------------------------
# Allowed characters for field / table identifiers embedded in SQL.
# Only letters (uppercase and lowercase), digits and underscore are permitted.
# Table-qualified names (e.g. "b.status") split on "." and each part is
# checked independently.
# ---------------------------------------------------------------------------
_SAFE_IDENT_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# Known lookup operators and the SQL fragments they produce.
# Values are *always* passed as bound parameters (represented by "?"),
# never string-interpolated.
_OPERATORS = {
    "exact",
    "iexact",
    "contains",
    "icontains",
    "startswith",
    "endswith",
    "gt",
    "gte",
    "lt",
    "lte",
    "isnull",
    "in",
}


def _validate_identifier(name: str) -> str:
    """Validate that *name* is a safe SQL identifier.

    Supports simple names (``id``) and table-qualified names (``b.id``).
    Raises ``ValueError`` if *name* contains characters outside the safe set
    or is empty.
    """
    for part in name.split("."):
        if not part or not all(c in _SAFE_IDENT_CHARS for c in part):
            raise ValueError(
                f"Unsafe identifier {name!r}: only letters, digits and "
                "underscores are allowed."
            )
    return name


def _validate_order_field(field: str) -> str:
    """Validate an ``order_by`` field, which may be prefixed with ``'-'``."""
    desc = field.startswith("-")
    _validate_identifier(field[1:] if desc else field)
    return field


# ---------------------------------------------------------------------------
# Result conversion helpers
# ---------------------------------------------------------------------------


def _convert_row(row: Any) -> Optional[Dict]:
    """Convert a single D1 result row to a plain Python dict."""
    if row is None:
        return None
    if hasattr(row, "to_py"):
        return row.to_py()
    if isinstance(row, dict):
        return dict(row)
    return None


def _convert_results(results: Any) -> List[Dict]:
    """Convert D1 ``results`` (list or JS proxy) to a Python list of dicts."""
    if results is None:
        return []
    if hasattr(results, "to_py"):
        converted = results.to_py()
        return converted if isinstance(converted, list) else []
    if isinstance(results, list):
        return [r for r in (_convert_row(row) for row in results) if r is not None]
    return []


# ---------------------------------------------------------------------------
# QuerySet
# ---------------------------------------------------------------------------


class QuerySet:
    """Lazy, chainable query builder for a single D1 table.

    All method calls return a *new* ``QuerySet`` instance so the original is
    never mutated (same contract as Django's ORM).

    Only field **names** are embedded in the generated SQL (after validation).
    All **values** are always passed as bound parameters so user-controlled
    data can never alter the query structure.
    """

    def __init__(self, model_class: "Type[Model]", db: Any) -> None:
        self._model = model_class
        self._db = db
        # Each entry: (field, operator, value)
        self._filters: List[Tuple[str, str, Any]] = []
        self._excludes: List[Tuple[str, str, Any]] = []
        self._limit_val: Optional[int] = None
        self._offset_val: int = 0
        self._order_by_fields: List[str] = []
        self._select_fields: List[str] = []
        # Each entry: (join_type, table, on_clause)
        self._joins: List[Tuple[str, str, str]] = []

    # ------------------------------------------------------------------
    # Cloning
    # ------------------------------------------------------------------

    def _clone(self) -> "QuerySet":
        qs = QuerySet(self._model, self._db)
        qs._filters = list(self._filters)
        qs._excludes = list(self._excludes)
        qs._limit_val = self._limit_val
        qs._offset_val = self._offset_val
        qs._order_by_fields = list(self._order_by_fields)
        qs._select_fields = list(self._select_fields)
        qs._joins = list(self._joins)
        return qs

    # ------------------------------------------------------------------
    # Chainable builders
    # ------------------------------------------------------------------

    def filter(self, **kwargs: Any) -> "QuerySet":
        """Narrow results to rows that match *all* keyword conditions.

        Keyword format: ``field=value`` or ``field__operator=value``.
        Example operators: ``exact`` (default), ``icontains``, ``gt``,
        ``gte``, ``lt``, ``lte``, ``in``, ``isnull``, ``startswith``,
        ``endswith``.
        """
        qs = self._clone()
        for key, value in kwargs.items():
            field, op = self._parse_lookup(key)
            qs._filters.append((field, op, value))
        return qs

    def exclude(self, **kwargs: Any) -> "QuerySet":
        """Exclude rows matching the keyword conditions."""
        qs = self._clone()
        for key, value in kwargs.items():
            field, op = self._parse_lookup(key)
            qs._excludes.append((field, op, value))
        return qs

    def order_by(self, *fields: str) -> "QuerySet":
        """Set the ``ORDER BY`` clause.  Prefix a field with ``'-'`` for DESC."""
        qs = self._clone()
        qs._order_by_fields = [_validate_order_field(f) for f in fields]
        return qs

    def limit(self, n: int) -> "QuerySet":
        """Limit the number of rows returned."""
        if not isinstance(n, int) or n < 0:
            raise ValueError("limit() requires a non-negative integer.")
        qs = self._clone()
        qs._limit_val = n
        return qs

    def offset(self, n: int) -> "QuerySet":
        """Skip the first *n* rows."""
        if not isinstance(n, int) or n < 0:
            raise ValueError("offset() requires a non-negative integer.")
        qs = self._clone()
        qs._offset_val = n
        return qs

    def values(self, *fields: str) -> "QuerySet":
        """Select only the specified columns (validated identifiers)."""
        qs = self._clone()
        qs._select_fields = [_validate_identifier(f) for f in fields]
        return qs

    def join(
        self,
        table: str,
        on: str,
        join_type: str = "INNER",
    ) -> "QuerySet":
        """Add a JOIN clause to the query.

        :param table: The table name to join (validated).
        :param on: The ON condition, e.g. ``"bugs.domain_id = domains.id"``.
                   Both sides are validated as safe identifiers.
                   Only a single equality condition is supported;
                   compound conditions (e.g. ``AND``) are not allowed.
        :param join_type: ``"INNER"``, ``"LEFT"``, ``"RIGHT"`` or ``"FULL"``.
                          Defaults to ``"INNER"``.

        Example::

            Bug.objects(db)\
                .join("domains", on="bugs.domain_id = domains.id", join_type="LEFT")\
                .filter(status="open")\
                .values("bugs.id", "bugs.title", "domains.name")\
                .all()
        """
        join_type = join_type.upper()
        if join_type not in {"INNER", "LEFT", "RIGHT", "FULL"}:
            raise ValueError(
                f"Unsupported join_type {join_type!r}. "
                "Use INNER, LEFT, RIGHT or FULL."
            )
        _validate_identifier(table)
        # Validate each side of the ON clause (exact format: "a.b = c.d").
        # Reject any extra tokens (e.g., "OR 1") even if whitespace is folded.
        match = re.match(r"^\s*([A-Za-z0-9_.]+)\s*=\s*([A-Za-z0-9_.]+)\s*$", on)
        if not match:
            raise ValueError(
                f"Invalid ON clause {on!r}. Expected format: 'table1.col = table2.col'."
            )
        lhs, rhs = match.group(1), match.group(2)
        _validate_identifier(lhs)
        _validate_identifier(rhs)
        # Store canonical form (no spaces) to prevent whitespace-folding bypasses
        canonical_on = f"{lhs} = {rhs}"

        qs = self._clone()
        qs._joins.append((join_type, table, canonical_on))
        return qs

    def paginate(self, page: int = 1, per_page: int = 20) -> "QuerySet":
        """Apply ``LIMIT``/``OFFSET`` pagination in a single call.

        *page* is 1-indexed.  *per_page* is clamped to ``[1, 100]``.
        """
        per_page = max(1, min(100, int(per_page)))
        page = max(1, int(page))
        return self.limit(per_page).offset((page - 1) * per_page)

    # ------------------------------------------------------------------
    # Lookup parsing
    # ------------------------------------------------------------------

    def _parse_lookup(self, key: str) -> Tuple[str, str]:
        """Parse ``'field__operator'`` into ``(field, operator)``."""
        parts = key.split("__")
        if len(parts) == 1:
            return _validate_identifier(parts[0]), "exact"
        # The last segment might be a known operator.
        candidate_op = parts[-1]
        if candidate_op in _OPERATORS:
            field = "__".join(parts[:-1])
            return _validate_identifier(field), candidate_op
        # No recognised operator – treat the whole key as a field name.
        return _validate_identifier(key), "exact"

    # ------------------------------------------------------------------
    # WHERE clause builder
    # ------------------------------------------------------------------

    def _build_condition(
        self, field: str, op: str, value: Any
    ) -> Tuple[str, List[Any]]:
        """Build one SQL condition fragment and its parameter list."""
        if op == "exact":
            return f"{field} = ?", [value]
        if op == "iexact":
            return f"LOWER({field}) = LOWER(?)", [value]
        if op == "contains":
            return f"{field} LIKE ?", [f"%{value}%"]
        if op == "icontains":
            return f"LOWER({field}) LIKE LOWER(?)", [f"%{value}%"]
        if op == "startswith":
            return f"{field} LIKE ?", [f"{value}%"]
        if op == "endswith":
            return f"{field} LIKE ?", [f"%{value}"]
        if op == "gt":
            return f"{field} > ?", [value]
        if op == "gte":
            return f"{field} >= ?", [value]
        if op == "lt":
            return f"{field} < ?", [value]
        if op == "lte":
            return f"{field} <= ?", [value]
        if op == "isnull":
            return (f"{field} IS NULL", []) if value else (f"{field} IS NOT NULL", [])
        if op == "in":
            if not value:
                # Empty IN clause – no rows can match.
                return "1 = 0", []
            placeholders = ", ".join(["?"] * len(value))
            return f"{field} IN ({placeholders})", list(value)
        raise ValueError(f"Unsupported lookup operator: {op!r}")

    def _build_where_clause(self) -> Tuple[str, List[Any]]:
        """Return ``(where_sql, params)`` for the current filters/excludes."""
        conditions: List[str] = []
        params: List[Any] = []

        for field, op, value in self._filters:
            cond, p = self._build_condition(field, op, value)
            conditions.append(cond)
            params.extend(p)

        for field, op, value in self._excludes:
            cond, p = self._build_condition(field, op, value)
            conditions.append(f"NOT ({cond})")
            params.extend(p)

        if conditions:
            return "WHERE " + " AND ".join(conditions), params
        return "", []

    # ------------------------------------------------------------------
    # Full query builder
    # ------------------------------------------------------------------

    def _build_from_with_joins_sql(self) -> str:
        """Return the FROM clause with all JOIN clauses appended.

        Used by both ``_build_select_sql()`` and ``count()`` to avoid
        duplicating FROM+JOIN assembly logic.
        """
        table = self._model.table_name
        sql = f"FROM {table}"
        for join_type, join_table, on_clause in self._joins:
            sql += f" {join_type} JOIN {join_table} ON {on_clause}"
        return sql

    def _build_select_sql(self) -> Tuple[str, List[Any]]:
        """Build the full ``SELECT`` SQL and its parameter list."""
        select = ", ".join(self._select_fields) if self._select_fields else "*"

        where, params = self._build_where_clause()
        sql = f"SELECT {select} {self._build_from_with_joins_sql()}"

        if where:
            sql += f" {where}"

        if self._order_by_fields:
            order_parts = [
                f"{f[1:]} DESC" if f.startswith("-") else f"{f} ASC"
                for f in self._order_by_fields
            ]
            sql += " ORDER BY " + ", ".join(order_parts)

        if self._limit_val is not None:
            sql += " LIMIT ?"
            params.append(self._limit_val)

        if self._offset_val:
            sql += " OFFSET ?"
            params.append(self._offset_val)

        return sql, params

    # ------------------------------------------------------------------
    # Async query executors
    # ------------------------------------------------------------------

    async def all(self) -> List[Dict]:
        """Execute and return all matching rows as a list of dicts."""
        sql, params = self._build_select_sql()
        result = await self._db.prepare(sql).bind(*params).all()
        return _convert_results(result.results if hasattr(result, "results") else [])

    async def first(self) -> Optional[Dict]:
        """Return the first matching row, or ``None`` if none matches."""
        sql, params = self.limit(1)._build_select_sql()
        result = await self._db.prepare(sql).bind(*params).first()
        return _convert_row(result)

    async def get(self, **kwargs: Any) -> Optional[Dict]:
        """Return the single row matching *kwargs*, or ``None``."""
        return await self.filter(**kwargs).first()

    async def count(self) -> int:
        """Return the number of rows matching the current filters.

        JOIN clauses (if any) are included so that filters on joined
        columns produce consistent results with ``all()`` and ``first()``.

        Note: The ON clause only supports simple equality conditions of the
        form ``table1.col = table2.col``. Compound ON conditions are not
        currently supported.
        """
        where, params = self._build_where_clause()
        sql = f"SELECT COUNT(*) AS total {self._build_from_with_joins_sql()}"
        if where:
            sql += f" {where}"
        result = await self._db.prepare(sql).bind(*params).first()
        row = _convert_row(result)
        return int(row["total"]) if row and row.get("total") is not None else 0

    async def exists(self) -> bool:
        """Return ``True`` if at least one matching row exists."""
        return (await self.count()) > 0

    async def update(self, **kwargs: Any) -> None:
        """Update all matching rows with the supplied field=value pairs.

        Raises ``ValueError`` if the QuerySet has active JOINs, as UPDATE
        with JOIN is not supported by this ORM.
        """
        if self._joins:
            raise ValueError(
                "update() is not supported on QuerySets with active JOINs. "
                "Remove .join() calls before calling .update()."
            )
        if not kwargs:
            return
        table = self._model.table_name
        set_parts: List[str] = []
        set_params: List[Any] = []
        for field, value in kwargs.items():
            _validate_identifier(field)
            set_parts.append(f"{field} = ?")
            set_params.append(value)

        where, where_params = self._build_where_clause()
        sql = f"UPDATE {table} SET " + ", ".join(set_parts)
        if where:
            sql += f" {where}"
        await self._db.prepare(sql).bind(*set_params, *where_params).run()

    async def delete(self) -> None:
        """Delete all matching rows.

        Raises ``ValueError`` if the QuerySet has active JOINs, as DELETE
        with JOIN is not supported by this ORM.
        """
        if self._joins:
            raise ValueError(
                "delete() is not supported on QuerySets with active JOINs. "
                "Remove .join() calls before calling .delete()."
            )
        table = self._model.table_name
        where, params = self._build_where_clause()
        sql = f"DELETE FROM {table}"
        if where:
            sql += f" {where}"
        await self._db.prepare(sql).bind(*params).run()


# ---------------------------------------------------------------------------
# Model base class
# ---------------------------------------------------------------------------


class Model:
    """Base class for ORM models.

    Subclasses **must** define ``table_name`` (a plain string constant that
    matches the actual SQLite table name).  Because ``table_name`` is a
    class attribute set by the developer – not derived from user input – it is
    safe to embed directly in SQL.

    Example::

        class Domain(Model):
            table_name = "domains"

        # Retrieve active domains
        domains = await Domain.objects(db).filter(is_active=1).order_by('-created').all()
    """

    table_name: str = ""

    @classmethod
    def objects(cls, db: Any) -> QuerySet:
        """Return a fresh :class:`QuerySet` bound to *db* for this model."""
        return QuerySet(cls, db)

    @classmethod
    async def create(cls, db: Any, **kwargs: Any) -> Optional[Dict]:
        """Insert a new row and return the created record as a dict.

        All field names are validated; all values are parameterized.
        """
        if not kwargs:
            raise ValueError("create() requires at least one field.")

        fields = list(kwargs.keys())
        for f in fields:
            _validate_identifier(f)

        values = list(kwargs.values())
        columns = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(fields))
        sql = f"INSERT INTO {cls.table_name} ({columns}) VALUES ({placeholders})"
        await db.prepare(sql).bind(*values).run()

        # Fetch the newly inserted row.
        id_result = await db.prepare("SELECT last_insert_rowid() AS id").first()
        row = _convert_row(id_result)
        if row and row.get("id"):
            return await QuerySet(cls, db).get(id=row["id"])
        return None

    @classmethod
    async def get_by_id(cls, db: Any, pk: int) -> Optional[Dict]:
        """Fetch a single row by primary key, or ``None`` if not found."""
        return await QuerySet(cls, db).get(id=pk)

    @classmethod
    async def update_by_id(cls, db: Any, pk: int, **kwargs: Any) -> None:
        """Update the row with the given primary key."""
        await QuerySet(cls, db).filter(id=pk).update(**kwargs)
