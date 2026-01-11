"""
File upload and processing handlers for the Chainlit UI.

Handles PDF, images, and text file ingestion.
"""

import mimetypes
from pathlib import Path
from typing import Any

import aiofiles
import chainlit as cl
import httpx
from pypdf import PdfReader

from penny_knowledge_core.config import get_settings
from penny_knowledge_core.logging import get_logger

logger = get_logger(__name__)


# Supported file types
SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "text",
    "text/markdown": "markdown",
    "text/csv": "csv",
    "application/json": "json",
    "image/png": "image",
    "image/jpeg": "image",
    "image/gif": "image",
    "image/webp": "image",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


async def handle_file_upload(
    elements: list[cl.Element],
    profile: str | None = None,
    space_id: str | None = None,
) -> None:
    """
    Handle uploaded files and ingest them into the knowledge graph.

    Args:
        elements: List of uploaded file elements
        profile: Current profile context
        space_id: Target space for ingestion
    """
    if not space_id:
        await cl.Message(
            content="Please set a default space ID in settings before uploading files.",
            author="System",
        ).send()
        return

    results: list[str] = []

    for element in elements:
        if not isinstance(element, cl.File):
            continue

        try:
            result = await process_file(element, profile, space_id)
            results.append(f"**{element.name}**: {result}")
        except Exception as e:
            logger.exception(f"Error processing file: {element.name}")
            results.append(f"**{element.name}**: Error - {str(e)}")

    if results:
        await cl.Message(
            content="## File Upload Results\n\n" + "\n".join(results),
            author="PENNY",
        ).send()


async def process_file(
    element: cl.File,
    profile: str | None,
    space_id: str,
) -> str:
    """
    Process a single uploaded file.

    Args:
        element: The uploaded file element
        profile: Current profile
        space_id: Target space

    Returns:
        Status message about the ingestion
    """
    file_path = Path(element.path)

    # Check file size
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        return f"File too large ({file_size / 1024 / 1024:.1f}MB). Max: 10MB"

    # Determine file type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type not in SUPPORTED_TYPES:
        return f"Unsupported file type: {mime_type}"

    file_type = SUPPORTED_TYPES[mime_type]

    # Extract content based on type
    if file_type == "pdf":
        content = await extract_pdf_content(file_path)
    elif file_type == "image":
        content = await process_image(file_path, element.name)
    else:
        content = await extract_text_content(file_path)

    if not content:
        return "Could not extract content from file"

    # Create a step to show processing
    async with cl.Step(name="Ingesting File", type="tool") as step:
        step.input = f"File: {element.name}\nType: {file_type}\nSize: {file_size / 1024:.1f}KB"

        # Ingest via gateway
        result = await ingest_content(
            content=content,
            space_id=space_id,
            profile=profile,
            type_hint=get_type_hint(file_type, element.name),
            source_name=element.name,
        )

        step.output = result

    return result


async def extract_pdf_content(file_path: Path) -> str:
    """Extract text content from a PDF file."""
    try:
        reader = PdfReader(str(file_path))
        text_parts: list[str] = []

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Page {i + 1} ---\n{page_text}")

        return "\n\n".join(text_parts)

    except Exception as e:
        logger.exception("PDF extraction error")
        raise ValueError(f"Failed to extract PDF: {e}")


async def extract_text_content(file_path: Path) -> str:
    """Extract content from a text-based file."""
    async with aiofiles.open(file_path, mode="r", encoding="utf-8", errors="ignore") as f:
        content = await f.read()
    return content


async def process_image(file_path: Path, filename: str) -> str:
    """
    Process an image file.

    For now, creates a reference object. Future: OCR or vision API.
    """
    # Create a simple description
    return f"[Image: {filename}]\n\nImage file uploaded. To extract text from this image, OCR processing would be required."


def get_type_hint(file_type: str, filename: str) -> str:
    """Determine the best type hint based on file type and name."""
    filename_lower = filename.lower()

    # Special patterns
    if "invoice" in filename_lower:
        return "Invoice"
    if "receipt" in filename_lower:
        return "Receipt"
    if "contract" in filename_lower:
        return "Contract"
    if "meeting" in filename_lower or "notes" in filename_lower:
        return "Note"
    if "article" in filename_lower or "paper" in filename_lower:
        return "Article"

    # Default by file type
    type_defaults = {
        "pdf": "Document",
        "text": "Note",
        "markdown": "Note",
        "csv": "Data",
        "json": "Data",
        "image": "Image",
    }

    return type_defaults.get(file_type, "Note")


async def ingest_content(
    content: str,
    space_id: str,
    profile: str | None,
    type_hint: str,
    source_name: str,
) -> str:
    """
    Ingest content via the gateway API.

    Args:
        content: Extracted content to ingest
        space_id: Target space
        profile: Current profile
        type_hint: Suggested object type
        source_name: Original filename

    Returns:
        Status message
    """
    settings = get_settings()
    gateway_url = f"http://localhost:{settings.gateway_port}"

    payload = {
        "content": content,
        "space_id": space_id,
        "type_hint": type_hint,
        "auto_link": True,
    }

    if profile:
        payload["profile_name"] = profile

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # First try the smart ingest endpoint
            response = await client.post(
                f"{gateway_url}/api/v1/objects",
                json={
                    "space_id": space_id,
                    "type_id": "note",  # Default to note type
                    "name": source_name,
                    "fields": {
                        "description": content[:5000],  # Truncate for large files
                        "source": source_name,
                    },
                    "profile_name": profile,
                },
            )

            if response.status_code >= 400:
                return f"Gateway error: {response.status_code}"

            data = response.json()
            obj_id = data.get("object", {}).get("id", "unknown")
            return f"Created object `{obj_id}` as {type_hint}"

    except httpx.ConnectError:
        return "Cannot connect to gateway. Is penny-gateway running?"
    except Exception as e:
        logger.exception("Ingestion error")
        return f"Error: {str(e)}"


# =============================================================================
# Quick Actions
# =============================================================================


async def create_quick_actions() -> list[cl.Action]:
    """Create quick action buttons for common operations."""
    return [
        cl.Action(
            name="create_space",
            label="New Space",
            description="Create a new space",
            icon="folder-plus",
        ),
        cl.Action(
            name="search",
            label="Search",
            description="Search your knowledge graph",
            icon="search",
        ),
        cl.Action(
            name="daily_briefing",
            label="Briefing",
            description="Get your daily briefing",
            icon="newspaper",
        ),
    ]
