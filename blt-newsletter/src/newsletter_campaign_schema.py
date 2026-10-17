def normalize_column_names(column_names):
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


def normalize_table_names(table_names):
    return normalize_column_names(table_names)


def campaign_table_name(table_names):
    names = normalize_table_names(table_names)
    if "newsletter_campaigns" in names:
        return "newsletter_campaigns"
    if "newsletter_issues" in names:
        return "newsletter_issues"

    return "newsletter_campaigns"


def campaign_slug_column(column_names):
    names = normalize_column_names(column_names)
    if "slug" in names:
        return "slug"
    if "issue_slug" in names:
        return "issue_slug"

    return "slug"


def campaign_select_columns(column_names, include_created_by=True):
    names = normalize_column_names(column_names)
    slug_column = campaign_slug_column(names)
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


def campaign_order_expression(column_names):
    names = normalize_column_names(column_names)
    if "published_at" in names:
        return "COALESCE(NULLIF(published_at, ''), created_at)"

    return "created_at"


def campaign_insert_columns_and_params(record, column_names):
    names = normalize_column_names(column_names)
    insert_pairs = [
        ("id", "id"),
        (campaign_slug_column(names), "slug"),
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


def map_campaign_update_fields(updates, column_names):
    names = normalize_column_names(column_names)
    mapped = {}

    for column, value in updates.items():
        target_column = column
        if column == "slug":
            target_column = campaign_slug_column(names)

        if target_column not in names:
            continue

        mapped[target_column] = value

    return mapped


def send_job_campaign_column(column_names):
    names = normalize_column_names(column_names)
    if "campaign_id" in names:
        return "campaign_id"
    if "issue_id" in names:
        return "issue_id"

    return "campaign_id"
