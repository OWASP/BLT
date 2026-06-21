def normalize_issue_columns(column_names):
    names = set()
    for column in column_names or []:
        if isinstance(column, str):
            name = column
        elif isinstance(column, dict):
            name = column.get("name")
        else:
            name = getattr(column, "name", None)

        if isinstance(name, str) and name:
            names.add(name)

    return names


def issue_slug_column(column_names):
    names = normalize_issue_columns(column_names)
    if "slug" in names:
        return "slug"
    if "issue_slug" in names:
        return "issue_slug"

    return "slug"


def issue_select_columns(column_names, include_created_by=True):
    names = normalize_issue_columns(column_names)
    slug_column = issue_slug_column(names)
    columns = [
        "id",
        "slug" if slug_column == "slug" else f"{slug_column} AS slug",
        "title",
        "subject",
        "summary" if "summary" in names else "'' AS summary",
        "status",
        "markdown_body",
        "html_body",
        "scheduled_for",
        "published_at" if "published_at" in names else "'' AS published_at",
        "sent_at",
    ]

    if include_created_by:
        columns.append(
            "created_by_admin_id" if "created_by_admin_id" in names else "'' AS created_by_admin_id"
        )

    columns.extend(["created_at", "updated_at", "metadata_json"])
    return columns


def issue_order_expression(column_names):
    names = normalize_issue_columns(column_names)
    if "published_at" in names:
        return "COALESCE(NULLIF(published_at, ''), created_at)"

    return "created_at"


def issue_insert_columns_and_params(record, column_names):
    names = normalize_issue_columns(column_names)
    insert_pairs = [
        ("id", "id"),
        (issue_slug_column(names), "slug"),
        ("title", "title"),
        ("subject", "subject"),
        ("summary", "summary"),
        ("status", "status"),
        ("markdown_body", "markdown_body"),
        ("html_body", "html_body"),
        ("scheduled_for", "scheduled_for"),
        ("published_at", "published_at"),
        ("sent_at", "sent_at"),
        ("created_by_admin_id", "created_by_admin_id"),
        ("created_at", "created_at"),
        ("updated_at", "updated_at"),
        ("metadata_json", "metadata_json"),
    ]
    columns = []
    params = []

    for column, record_key in insert_pairs:
        if column not in names:
            continue
        columns.append(column)
        params.append(record.get(record_key))

    return columns, params


def map_issue_update_fields(updates, column_names):
    names = normalize_issue_columns(column_names)
    mapped = {}

    for column, value in updates.items():
        target_column = column
        if column == "slug":
            target_column = issue_slug_column(names)

        if target_column not in names:
            continue

        mapped[target_column] = value

    return mapped
