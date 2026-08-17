"""Pipeline — queue consumer and cron poller entry points."""

from .consumer import process_pipeline_event

__all__ = ["process_pipeline_event"]
