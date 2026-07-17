import logging
from typing import List, Optional
from blt_mcp.server_base import mcp, http_client
from blt_mcp.tools import generate_ai_metadata

logger = logging.getLogger("blt-mcp.v2_tools")


@mcp.tool()
async def auth_signup(
    email: str, password: str, username: str, confirmed: bool = False
) -> str:
    """
    Create a new user account.
    """
    if not confirmed:
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info(f"Signing up user: {username}")
    ai_metadata = generate_ai_metadata("auth_signup")
    payload = {
        "email": email,
        "password": password,
        "username": username,
        "metadata": ai_metadata,
    }
    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }
    try:
        response = await http_client.post(
            "/v2/auth/signup", json=payload, headers=headers
        )
        response.raise_for_status()
        return f"Successfully created account for: {username}"
    except Exception as e:
        logger.error(f"Failed to sign up: {e}")
        raise RuntimeError(f"Failed to sign up: {e}") from e


@mcp.tool()
async def auth_signin(email: str, password: str) -> str:
    """
    Sign in to retrieve a session or authentication token.
    """
    logger.info(f"Signing in user: {email}")
    payload = {"email": email, "password": password}
    try:
        response = await http_client.post("/v2/auth/signin", json=payload)
        response.raise_for_status()
        return f"Successfully signed in: {response.text}"
    except Exception as e:
        logger.error(f"Failed to sign in: {e}")
        raise RuntimeError(f"Failed to sign in: {e}") from e


@mcp.tool()
async def create_bug(
    title: str,
    description: str,
    repo_id: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignee: Optional[str] = None,
    confirmed: bool = False,
) -> str:
    """
    Create a new bug report in v2 API.
    """
    if not confirmed:
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info(f"Creating v2 bug: {title}")
    ai_metadata = generate_ai_metadata("create_bug")
    payload = {"title": title, "description": description, "metadata": ai_metadata}
    if repo_id is not None:
        payload["repo_id"] = repo_id
    if labels is not None:
        payload["labels"] = labels
    if assignee is not None:
        payload["assignee"] = assignee

    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }
    try:
        response = await http_client.post("/v2/bugs", json=payload, headers=headers)
        response.raise_for_status()
        return f"Successfully created bug: {title}"
    except Exception as e:
        logger.error(f"Failed to create bug: {e}")
        raise RuntimeError(f"Failed to create bug: {e}") from e


@mcp.tool()
async def update_bug(
    id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    confirmed: bool = False,
) -> str:
    """
    Update an existing bug by ID.
    """
    if not confirmed:
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info(f"Updating v2 bug: {id}")
    ai_metadata = generate_ai_metadata("update_bug")
    payload = {"metadata": ai_metadata}
    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    if status is not None:
        payload["status"] = status

    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }
    try:
        response = await http_client.patch(
            f"/v2/bugs/{id}", json=payload, headers=headers
        )
        response.raise_for_status()
        return f"Successfully updated bug: {id}"
    except Exception as e:
        logger.error(f"Failed to update bug: {e}")
        raise RuntimeError(f"Failed to update bug: {e}") from e


@mcp.tool()
async def create_user(
    username: str,
    email: str,
    password: str,
    profile_info: Optional[str] = None,
    confirmed: bool = False,
) -> str:
    """
    Create a new user.
    """
    if not confirmed:
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info(f"Creating v2 user: {username}")
    ai_metadata = generate_ai_metadata("create_user")
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "metadata": ai_metadata,
    }
    if profile_info is not None:
        payload["profile_info"] = profile_info

    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }
    try:
        response = await http_client.post("/v2/users", json=payload, headers=headers)
        response.raise_for_status()
        return f"Successfully created user: {username}"
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise RuntimeError(f"Failed to create user: {e}") from e


@mcp.tool()
async def create_job(
    title: str,
    description: str,
    company: str,
    location: Optional[str] = None,
    confirmed: bool = False,
) -> str:
    """
    Create a new job posting.
    """
    if not confirmed:
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info(f"Creating v2 job: {title} at {company}")
    ai_metadata = generate_ai_metadata("create_job")
    payload = {
        "title": title,
        "description": description,
        "company": company,
        "metadata": ai_metadata,
    }
    if location is not None:
        payload["location"] = location

    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }
    try:
        response = await http_client.post("/v2/jobs", json=payload, headers=headers)
        response.raise_for_status()
        return f"Successfully created job: {title}"
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise RuntimeError(f"Failed to create job: {e}") from e


@mcp.tool()
async def update_job(
    id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    confirmed: bool = False,
) -> str:
    """
    Update an existing job posting.
    """
    if not confirmed:
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info(f"Updating v2 job: {id}")
    ai_metadata = generate_ai_metadata("update_job")
    payload = {"metadata": ai_metadata}
    if title is not None:
        payload["title"] = title
    if description is not None:
        payload["description"] = description
    if company is not None:
        payload["company"] = company
    if location is not None:
        payload["location"] = location

    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }
    try:
        response = await http_client.patch(
            f"/v2/jobs/{id}", json=payload, headers=headers
        )
        response.raise_for_status()
        return f"Successfully updated job: {id}"
    except Exception as e:
        logger.error(f"Failed to update job: {e}")
        raise RuntimeError(f"Failed to update job: {e}") from e


@mcp.tool()
async def record_job_view(id: str, confirmed: bool = False) -> str:
    """
    Record a view for a job.
    """
    if not confirmed:
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info(f"Recording view for job: {id}")
    ai_metadata = generate_ai_metadata("record_job_view")
    payload = {"metadata": ai_metadata}
    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }
    try:
        response = await http_client.post(
            f"/v2/jobs/{id}/view", json=payload, headers=headers
        )
        response.raise_for_status()
        return f"Successfully recorded view for job: {id}"
    except Exception as e:
        logger.error(f"Failed to record job view: {e}")
        raise RuntimeError(f"Failed to record job view: {e}") from e


@mcp.tool()
async def create_hackathon(
    name: str,
    description: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    confirmed: bool = False,
) -> str:
    """
    Create a new hackathon.
    """
    if not confirmed:
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info(f"Creating v2 hackathon: {name}")
    ai_metadata = generate_ai_metadata("create_hackathon")
    payload = {"name": name, "description": description, "metadata": ai_metadata}
    if start_date is not None:
        payload["start_date"] = start_date
    if end_date is not None:
        payload["end_date"] = end_date

    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }
    try:
        response = await http_client.post(
            "/v2/hackathons", json=payload, headers=headers
        )
        response.raise_for_status()
        return f"Successfully created hackathon: {name}"
    except Exception as e:
        logger.error(f"Failed to create hackathon: {e}")
        raise RuntimeError(f"Failed to create hackathon: {e}") from e


@mcp.tool()
async def update_hackathon(
    id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    confirmed: bool = False,
) -> str:
    """
    Update an existing hackathon.
    """
    if not confirmed:
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info(f"Updating v2 hackathon: {id}")
    ai_metadata = generate_ai_metadata("update_hackathon")
    payload = {"metadata": ai_metadata}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description

    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }
    try:
        response = await http_client.patch(
            f"/v2/hackathons/{id}", json=payload, headers=headers
        )
        response.raise_for_status()
        return f"Successfully updated hackathon: {id}"
    except Exception as e:
        logger.error(f"Failed to update hackathon: {e}")
        raise RuntimeError(f"Failed to update hackathon: {e}") from e


@mcp.tool()
async def register_hackathon_participant(
    id: str, user_id: str, confirmed: bool = False
) -> str:
    """
    Register a participant for a hackathon.
    """
    if not confirmed:
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info(f"Registering user {user_id} for hackathon {id}")
    ai_metadata = generate_ai_metadata("register_hackathon_participant")
    payload = {"user_id": user_id, "metadata": ai_metadata}
    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }
    try:
        response = await http_client.post(
            f"/v2/hackathons/{id}/register", json=payload, headers=headers
        )
        response.raise_for_status()
        return f"Successfully registered participant {user_id} for hackathon: {id}"
    except Exception as e:
        logger.error(f"Failed to register hackathon participant: {e}")
        raise RuntimeError(f"Failed to register hackathon participant: {e}") from e
