-- Migration 002: Health state tracking table
-- Provides durable health/status data for the /health and /status endpoints

CREATE TABLE IF NOT EXISTS health_state (
    component TEXT NOT NULL,
    field     TEXT NOT NULL,
    value     TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (component, field)
);
