ALTER TABLE events ADD COLUMN api_app_id TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN command TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN command_text TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN is_enterprise_install TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN response_url TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN team_domain TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN trigger_id TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN user_name TEXT DEFAULT '';
ALTER TABLE events ADD COLUMN slack_token TEXT DEFAULT '';

UPDATE events
SET
    api_app_id = COALESCE(json_extract(request_data, '$.api_app_id'), ''),
    command = COALESCE(json_extract(request_data, '$.command'), ''),
    command_text = COALESCE(json_extract(request_data, '$.text'), ''),
    is_enterprise_install = COALESCE(json_extract(request_data, '$.is_enterprise_install'), ''),
    response_url = COALESCE(json_extract(request_data, '$.response_url'), ''),
    team_domain = COALESCE(json_extract(request_data, '$.team_domain'), ''),
    trigger_id = COALESCE(json_extract(request_data, '$.trigger_id'), ''),
    user_name = COALESCE(json_extract(request_data, '$.user_name'), ''),
    slack_token = COALESCE(json_extract(request_data, '$.token'), '')
WHERE json_valid(request_data);
