"""
Input Validation and Protocol Interception Middleware for the BLT-MCP Server.

This module provides input validation schemas (`TOOL_SCHEMAS`) and stream interception classes
(`StdinWrapper`, `InterceptingStdinBuffer`) to validate JSON-RPC parameters before they reach the FastMCP server parser.

Key Offerings:
- **Parameter Validation**: Exposes `validate_tool_arguments(tool_name, arguments)` to validate tool calls
  against defined schemas (checks for required parameters, types, non-blank strings, and arrays).
- **JSON-RPC Interception**: Implements `InterceptingStdinBuffer` to intercept JSON-RPC stdin reads.
  - Returns clean client-visible JSON-RPC error frames (`code: -32602`) for invalid requests.
  - Automatically translates rejected payloads into dummy `ping` messages to prevent the MCP subprocess loop from crashing.

Schemas Defined:
- Includes schemas for `submit_issue`, `add_comment`, `summarize_issue_context`, `triage_vulnerability`, `draft_vision_issue`,
  and the entire set of V2 write tools.
"""

import sys


import json
import io
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("blt-mcp.validation")

TOOL_SCHEMAS = {
    "submit_issue": {
        "required": ["url", "title", "description"],
        "properties": {
            "url": {"type": str, "description": "The vulnerable URL being reported."},
            "title": {"type": str, "description": "Title of the bug/vulnerability."},
            "description": {
                "type": str,
                "description": "A detailed description of the bug or vulnerability.",
            },
            "severity": {"type": str, "description": "Severity level of the issue."},
            "bug_type": {"type": str, "description": "The type of bug."},
            "steps_to_reproduce": {
                "type": str,
                "description": "Step-by-step instructions.",
            },
            "labels": {
                "type": list,
                "item_type": str,
                "description": "Optional list of labels to apply to the issue.",
            },
            "assignee": {
                "type": str,
                "description": "Optional username of the assignee for the issue.",
            },
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "add_comment": {
        "required": ["issue_id", "comment_text"],
        "properties": {
            "issue_id": {
                "type": str,
                "description": "The ID of the issue to comment on.",
            },
            "comment_text": {"type": str, "description": "The text of the comment."},
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "summarize_issue_context": {
        "required": ["issue_id"],
        "properties": {
            "issue_id": {
                "type": str,
                "description": "The ID of the issue to summarize.",
            }
        },
    },
    "auth_signup": {
        "required": ["email", "password", "username"],
        "properties": {
            "email": {"type": str, "description": "The email of the user."},
            "password": {"type": str, "description": "The password of the user."},
            "username": {"type": str, "description": "The username of the user."},
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "auth_signin": {
        "required": ["email", "password"],
        "properties": {
            "email": {"type": str, "description": "The email of the user."},
            "password": {"type": str, "description": "The password of the user."},
        },
    },
    "create_bug": {
        "required": ["title", "description"],
        "properties": {
            "title": {"type": str, "description": "The title of the bug."},
            "description": {
                "type": str,
                "description": "A detailed description of the bug.",
            },
            "repo_id": {"type": str, "description": "The ID of the repository."},
            "labels": {
                "type": list,
                "item_type": str,
                "description": "Optional list of labels.",
            },
            "assignee": {
                "type": str,
                "description": "Optional username of the assignee.",
            },
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "update_bug": {
        "required": ["id"],
        "properties": {
            "id": {"type": str, "description": "The ID of the bug to update."},
            "title": {"type": str, "description": "Optional new title of the bug."},
            "description": {
                "type": str,
                "description": "Optional new description of the bug.",
            },
            "status": {"type": str, "description": "Optional new status of the bug."},
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "create_user": {
        "required": ["username", "email", "password"],
        "properties": {
            "username": {"type": str, "description": "The username of the user."},
            "email": {"type": str, "description": "The email of the user."},
            "password": {"type": str, "description": "The password of the user."},
            "profile_info": {
                "type": str,
                "description": "Optional profile information.",
            },
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "create_job": {
        "required": ["title", "description", "company"],
        "properties": {
            "title": {"type": str, "description": "The title of the job."},
            "description": {"type": str, "description": "The description of the job."},
            "company": {
                "type": str,
                "description": "The company name offering the job.",
            },
            "location": {"type": str, "description": "Optional location of the job."},
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "update_job": {
        "required": ["id"],
        "properties": {
            "id": {"type": str, "description": "The ID of the job to update."},
            "title": {"type": str, "description": "Optional new title of the job."},
            "description": {
                "type": str,
                "description": "Optional new description of the job.",
            },
            "company": {"type": str, "description": "Optional new company name."},
            "location": {"type": str, "description": "Optional new location."},
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "record_job_view": {
        "required": ["id"],
        "properties": {
            "id": {"type": str, "description": "The ID of the job to record view for."},
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "create_hackathon": {
        "required": ["name", "description"],
        "properties": {
            "name": {"type": str, "description": "The name of the hackathon."},
            "description": {
                "type": str,
                "description": "The description of the hackathon.",
            },
            "start_date": {
                "type": str,
                "description": "Optional start date of the hackathon.",
            },
            "end_date": {
                "type": str,
                "description": "Optional end date of the hackathon.",
            },
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "update_hackathon": {
        "required": ["id"],
        "properties": {
            "id": {"type": str, "description": "The ID of the hackathon to update."},
            "name": {"type": str, "description": "Optional new name of the hackathon."},
            "description": {
                "type": str,
                "description": "Optional new description of the hackathon.",
            },
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "register_hackathon_participant": {
        "required": ["id", "user_id"],
        "properties": {
            "id": {"type": str, "description": "The ID of the hackathon."},
            "user_id": {"type": str, "description": "The ID of the user to register."},
            "confirmed": {
                "type": bool,
                "description": "Must be set to true to execute this write operation.",
            },
        },
    },
    "triage_vulnerability": {
        "required": ["prompt"],
        "properties": {
            "prompt": {
                "type": str,
                "description": "The full prompt string containing the issue details to analyze.",
            }
        },
    },
    "draft_vision_issue": {
        "required": ["image_path"],
        "properties": {
            "image_path": {
                "type": str,
                "description": "Absolute path to the screenshot image on the local system.",
            },
            "gitlab_project_id": {
                "type": str,
                "description": "Optional GitLab project ID to upload the image to.",
            },
            "context": {
                "type": str,
                "description": "Optional user-provided context or hints about the screenshot.",
            },
        },
    },
}


def validate_tool_arguments(tool_name: str, arguments: dict) -> Optional[str]:
    """
    Validate tool arguments against defined tool schemas.
    Returns None if valid, or an error message string if invalid.
    """
    schema = TOOL_SCHEMAS.get(tool_name)
    if not schema:
        return f"Unknown tool '{tool_name}' - no validation schema found."

    # Check for required fields
    for req in schema["required"]:
        if req not in arguments:
            return f"Missing required parameter: '{req}'"
        val = arguments[req]
        if val is None:
            return f"Required parameter '{req}' cannot be null"
        if isinstance(val, str) and not val.strip():
            return f"Required parameter '{req}' cannot be empty"

    # Check types and constraints of provided parameters
    for key, val in arguments.items():
        if key not in schema["properties"]:
            return f"Unexpected parameter: '{key}'"

        if val is None:
            continue

        prop = schema["properties"][key]
        expected_type = prop["type"]

        if not isinstance(val, expected_type):
            return f"Parameter '{key}' must be of type {expected_type.__name__}, got {type(val).__name__}"

        if expected_type is list:
            item_type = prop.get("item_type")
            if item_type:
                for idx, item in enumerate(val):
                    if not isinstance(item, item_type):
                        return f"Item at index {idx} in parameter '{key}' must be of type {item_type.__name__}, got {type(item).__name__}"

        if expected_type is str and not val.strip():
            return f"Parameter '{key}' cannot be blank"

    return None


class InterceptingStdinBuffer(io.BufferedIOBase):
    def __init__(self, original):
        self.original = original
        self.buffer = b""

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return False

    @property
    def closed(self):
        return self.original.closed

    def read(self, size=-1):
        if not self.buffer:
            # Stdio transport runs line-by-line. Using readline() prevents blocking.
            chunk = self.original.readline()
            if not chunk:
                return b""

            self.buffer += chunk
            self._process_buffer()

        if size is not None and size > 0:
            res = self.buffer[:size]
            self.buffer = self.buffer[size:]
            return res
        else:
            res = self.buffer
            self.buffer = b""
            return res

    def read1(self, size=-1):
        return self.read(size)

    def readline(self, limit=-1):
        if b"\n" not in self.buffer:
            chunk = self.original.readline(limit)
            if chunk:
                self.buffer += chunk
                self._process_buffer()

        if b"\n" in self.buffer:
            idx = self.buffer.index(b"\n") + 1
            res = self.buffer[:idx]
            self.buffer = self.buffer[idx:]
            return res
        else:
            res = self.buffer
            self.buffer = b""
            return res

    def _process_buffer(self):
        lines = self.buffer.split(b"\n")
        processed_lines = []
        for line in lines[:-1]:
            decoded = line.decode("utf-8", errors="ignore").strip()
            if decoded:
                try:
                    data = json.loads(decoded)

                    # 1. Intercept resources/read missing URI
                    if (
                        isinstance(data, dict)
                        and data.get("method") == "resources/read"
                    ):
                        params = data.get("params")
                        if isinstance(params, dict) and "uri" not in params:
                            req_id = data.get("id")
                            error_resp = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32602,
                                    "message": "Invalid params: missing 'uri' parameter in resources/read",
                                },
                            }
                            sys.stdout.write(json.dumps(error_resp) + "\n")
                            sys.stdout.flush()

                            ping_req = {
                                "jsonrpc": "2.0",
                                "id": f"dummy_{req_id}",
                                "method": "ping",
                            }
                            processed_lines.append(json.dumps(ping_req).encode("utf-8"))
                            continue

                    # 2. Intercept tools/call validation
                    if isinstance(data, dict) and data.get("method") == "tools/call":
                        params = data.get("params")
                        if isinstance(params, dict):
                            tool_name = params.get("name")
                            arguments = params.get("arguments") or {}

                            if not isinstance(arguments, dict):
                                req_id = data.get("id")
                                error_resp = {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "error": {
                                        "code": -32602,
                                        "message": "Invalid params: 'arguments' must be an object",
                                    },
                                }
                                sys.stdout.write(json.dumps(error_resp) + "\n")
                                sys.stdout.flush()
                                logger.error(
                                    "Rejected malformed tools/call payload (arguments is not an object)"
                                )

                                ping_req = {
                                    "jsonrpc": "2.0",
                                    "id": f"dummy_{req_id}",
                                    "method": "ping",
                                }
                                processed_lines.append(
                                    json.dumps(ping_req).encode("utf-8")
                                )
                                continue

                            err_msg = validate_tool_arguments(tool_name, arguments)
                            if err_msg:
                                req_id = data.get("id")
                                error_resp = {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "error": {
                                        "code": -32602,
                                        "message": f"Validation error for tool '{tool_name}': {err_msg}",
                                    },
                                }
                                sys.stdout.write(json.dumps(error_resp) + "\n")
                                sys.stdout.flush()
                                logger.error(
                                    "Rejected invalid tools/call payload for '%s': %s",
                                    tool_name,
                                    err_msg,
                                )

                                ping_req = {
                                    "jsonrpc": "2.0",
                                    "id": f"dummy_{req_id}",
                                    "method": "ping",
                                }
                                processed_lines.append(
                                    json.dumps(ping_req).encode("utf-8")
                                )
                                continue

                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.exception("Unexpected error while intercepting stdin: %s", e)
            processed_lines.append(line)

        self.buffer = b"\n".join(processed_lines)
        if len(lines) > 1:
            self.buffer += b"\n" + lines[-1]


class StdinWrapper:
    def __init__(self, original_stdin, intercepted_buffer):
        self.original_stdin = original_stdin
        self.buffer = intercepted_buffer

    def __getattr__(self, name):
        return getattr(self.original_stdin, name)
