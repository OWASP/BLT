import os
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from blt_mcp import server_base
from blt_mcp.server import upload_screenshot


@pytest.fixture(autouse=True)
async def setup_http_client():
    """Setup a mock http_client for server_base."""
    original_client = server_base.http_client
    server_base.http_client = httpx.AsyncClient()

    # Ensure GITLAB_API_TOKEN is set for testing
    old_token = os.environ.get("GITLAB_API_TOKEN")
    os.environ["GITLAB_API_TOKEN"] = "test-token"

    yield

    await server_base.http_client.aclose()
    server_base.http_client = original_client
    if old_token is not None:
        os.environ["GITLAB_API_TOKEN"] = old_token
    else:
        os.environ.pop("GITLAB_API_TOKEN", None)


@pytest.fixture
def dummy_image(tmp_path):
    """Create a dummy image file in the approved root (or current directory)."""
    # Use approved root (default is current working dir)
    approved_root = Path(os.getenv("BLT_APPROVED_ROOT") or os.getcwd()).resolve()
    image_file = approved_root / "test_screenshot_dummy.png"
    image_file.write_bytes(b"dummy image content")
    yield str(image_file)
    # Clean up
    image_file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_upload_screenshot_invalid_project_id_validation_first(dummy_image):
    """Verify that an invalid project ID raises ValueError before any file read is performed."""
    with patch("anyio.to_thread.run_sync") as mock_run_sync:
        with pytest.raises(ValueError, match="Invalid GitLab project ID."):
            await upload_screenshot(
                image_path=dummy_image, gitlab_project_id="invalid project id spaces!!"
            )
        # Ensure file read via anyio was NOT called
        mock_run_sync.assert_not_called()


@pytest.mark.asyncio
async def test_upload_screenshot_valid_numeric_id(dummy_image):
    """Verify that a valid numeric GitLab project ID succeeds."""
    markdown_link = await upload_screenshot(
        image_path=dummy_image, gitlab_project_id="12345"
    )
    assert markdown_link == "![vuln](/uploads/vuln.png)"


@pytest.mark.asyncio
async def test_upload_screenshot_valid_namespace_id(dummy_image):
    """Verify that a URL-encoded/namespace project ID containing slashes is accepted and matched."""
    # This also tests the mock server regex match in server_base.py
    markdown_link = await upload_screenshot(
        image_path=dummy_image, gitlab_project_id="org/repo/subgroup"
    )
    assert markdown_link == "![vuln](/uploads/vuln.png)"


@pytest.mark.asyncio
async def test_upload_screenshot_missing_markdown(dummy_image):
    """Verify that if the response has status 201 but is missing the 'markdown' field, RuntimeError is raised."""

    async def mock_send_missing_markdown(self, request, *args, **kwargs):
        return httpx.Response(
            status_code=201, json={"other_field": "some_value"}, request=request
        )

    with (
        patch.object(httpx.AsyncClient, "send", mock_send_missing_markdown),
        pytest.raises(
            RuntimeError, match="GitLab upload succeeded but returned no markdown link."
        ),
    ):
        await upload_screenshot(image_path=dummy_image, gitlab_project_id="123")
