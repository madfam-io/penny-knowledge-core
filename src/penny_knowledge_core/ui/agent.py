"""
PENNY Agent - LLM-powered tool orchestration.

Handles message processing, tool selection, and response generation.
Supports both OpenAI and Anthropic backends.
"""

import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator

import httpx

from penny_knowledge_core.config import get_settings
from penny_knowledge_core.logging import get_logger

logger = get_logger(__name__)


class ChunkType(str, Enum):
    """Types of response chunks."""

    TEXT = "text"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    ERROR = "error"


@dataclass
class ResponseChunk:
    """A chunk of the streaming response."""

    type: ChunkType
    content: str = ""
    tool_name: str = ""
    tool_input: str = ""
    tool_output: str = ""


# =============================================================================
# Tool Definitions for LLM
# =============================================================================

PENNY_TOOLS = [
    {
        "name": "switch_profile",
        "description": "Switch to a different identity profile (personal, work, or research)",
        "parameters": {
            "type": "object",
            "properties": {
                "profile_name": {
                    "type": "string",
                    "description": "Profile to switch to",
                    "enum": ["personal", "work", "research"],
                }
            },
            "required": ["profile_name"],
        },
    },
    {
        "name": "create_space",
        "description": "Create a new AnyType space for organizing objects",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the new space",
                },
                "icon": {
                    "type": "string",
                    "description": "Optional emoji icon for the space",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_spaces",
        "description": "List all spaces in the current profile",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "create_object",
        "description": "Create a new object in a space",
        "parameters": {
            "type": "object",
            "properties": {
                "space_id": {
                    "type": "string",
                    "description": "Target space ID",
                },
                "type_id": {
                    "type": "string",
                    "description": "Object type ID",
                },
                "name": {
                    "type": "string",
                    "description": "Object name/title",
                },
                "fields": {
                    "type": "object",
                    "description": "Field values as key-value pairs",
                },
            },
            "required": ["space_id", "type_id", "name"],
        },
    },
    {
        "name": "search",
        "description": "Search for objects across the knowledge graph",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "space_id": {
                    "type": "string",
                    "description": "Optional: limit to specific space",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default 20)",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_graph_stats",
        "description": "Get statistics about the knowledge graph (spaces, types, objects count)",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "ensure_ontology",
        "description": "Create types and relations from a schema definition. Use this when the user wants to set up a CRM, project tracker, or any structured data.",
        "parameters": {
            "type": "object",
            "properties": {
                "space_id": {
                    "type": "string",
                    "description": "Target space ID",
                },
                "manifest": {
                    "type": "object",
                    "description": "Ontology manifest with 'name', 'types', and 'relations'",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, only report what would be created",
                    "default": False,
                },
            },
            "required": ["space_id", "manifest"],
        },
    },
    {
        "name": "smart_ingest",
        "description": "Intelligently ingest content (text, URLs) into structured objects",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Raw text, URL, or content to ingest",
                },
                "space_id": {
                    "type": "string",
                    "description": "Target space ID",
                },
                "type_hint": {
                    "type": "string",
                    "description": "Suggested type for the content",
                },
            },
            "required": ["content", "space_id"],
        },
    },
    {
        "name": "daily_briefing",
        "description": "Generate a summary of recent activity in the knowledge graph",
        "parameters": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "Lookback period in hours (default 24)",
                    "default": 24,
                },
                "space_id": {
                    "type": "string",
                    "description": "Optional: limit to specific space",
                },
            },
        },
    },
]


# Convert to OpenAI format
OPENAI_TOOLS = [
    {"type": "function", "function": tool}
    for tool in PENNY_TOOLS
]

# Convert to Anthropic format
ANTHROPIC_TOOLS = [
    {
        "name": tool["name"],
        "description": tool["description"],
        "input_schema": tool["parameters"],
    }
    for tool in PENNY_TOOLS
]


# =============================================================================
# PENNY Agent
# =============================================================================


class PennyAgent:
    """
    LLM-powered agent for PENNY Knowledge Core.

    Orchestrates tool calls based on user messages and streams responses.
    """

    def __init__(self) -> None:
        """Initialize the agent with API clients."""
        self.settings = get_settings()
        self.gateway_url = f"http://localhost:{self.settings.gateway_port}"

        # Determine LLM backend
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

        if not self.anthropic_key and not self.openai_key:
            logger.warning("No LLM API key found. Using mock responses.")

        self.use_anthropic = bool(self.anthropic_key)

    async def process_message(
        self,
        message: str,
        profile: str | None = None,
        space_id: str | None = None,
    ) -> AsyncIterator[ResponseChunk]:
        """
        Process a user message and yield response chunks.

        Args:
            message: The user's message
            profile: Current profile context
            space_id: Current space context

        Yields:
            ResponseChunk objects for streaming display
        """
        # Build system prompt with context
        system_prompt = self._build_system_prompt(profile, space_id)

        if self.anthropic_key:
            async for chunk in self._process_with_anthropic(message, system_prompt):
                yield chunk
        elif self.openai_key:
            async for chunk in self._process_with_openai(message, system_prompt):
                yield chunk
        else:
            async for chunk in self._process_mock(message, profile, space_id):
                yield chunk

    async def generate_briefing(
        self,
        profile: str | None = None,
        hours: int = 24,
    ) -> AsyncIterator[ResponseChunk]:
        """Generate a daily briefing."""
        result = await self._call_gateway_tool(
            "daily_briefing",
            {"hours": hours},
            profile,
        )
        yield ResponseChunk(type=ChunkType.TEXT, content=result)

    def _build_system_prompt(
        self,
        profile: str | None = None,
        space_id: str | None = None,
    ) -> str:
        """Build the system prompt with current context."""
        context_parts = [
            "You are PENNY, an intelligent knowledge concierge.",
            "You help users manage their personal knowledge graph using AnyType.",
            "",
            "## Current Context",
            f"- **Profile**: {profile or 'personal'}",
        ]

        if space_id:
            context_parts.append(f"- **Active Space**: {space_id}")

        context_parts.extend([
            "",
            "## Guidelines",
            "1. Use tools to interact with the knowledge graph - don't just describe what you would do",
            "2. Be concise but helpful",
            "3. When creating schemas, ask clarifying questions about required fields",
            "4. Always confirm before deleting anything",
            "5. Format responses in markdown for readability",
            "",
            "## Available Capabilities",
            "- Create and manage spaces",
            "- Design ontologies (types and relations)",
            "- Ingest content from text and URLs",
            "- Search across the knowledge graph",
            "- Generate activity briefings",
        ])

        return "\n".join(context_parts)

    async def _process_with_anthropic(
        self,
        message: str,
        system_prompt: str,
    ) -> AsyncIterator[ResponseChunk]:
        """Process with Anthropic Claude API."""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self.anthropic_key)

            messages = [{"role": "user", "content": message}]

            # Initial API call
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                tools=ANTHROPIC_TOOLS,
                messages=messages,
            )

            # Process response blocks
            while True:
                for block in response.content:
                    if block.type == "text":
                        yield ResponseChunk(type=ChunkType.TEXT, content=block.text)

                    elif block.type == "tool_use":
                        # Signal tool start
                        yield ResponseChunk(
                            type=ChunkType.TOOL_START,
                            tool_name=block.name,
                            tool_input=json.dumps(block.input, indent=2),
                        )

                        # Execute tool
                        tool_result = await self._execute_tool(block.name, block.input)

                        # Signal tool end
                        yield ResponseChunk(
                            type=ChunkType.TOOL_END,
                            tool_name=block.name,
                            tool_output=tool_result,
                        )

                        # Continue conversation with tool result
                        messages.append({"role": "assistant", "content": response.content})
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": tool_result,
                            }],
                        })

                # Check if we need to continue
                if response.stop_reason == "end_turn":
                    break
                elif response.stop_reason == "tool_use":
                    # Get next response
                    response = await client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4096,
                        system=system_prompt,
                        tools=ANTHROPIC_TOOLS,
                        messages=messages,
                    )
                else:
                    break

        except Exception as e:
            logger.exception("Anthropic API error")
            yield ResponseChunk(type=ChunkType.ERROR, content=str(e))

    async def _process_with_openai(
        self,
        message: str,
        system_prompt: str,
    ) -> AsyncIterator[ResponseChunk]:
        """Process with OpenAI API."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.openai_key)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ]

            while True:
                response = await client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    tools=OPENAI_TOOLS,
                    tool_choice="auto",
                )

                assistant_message = response.choices[0].message
                messages.append(assistant_message)

                # Handle text content
                if assistant_message.content:
                    yield ResponseChunk(type=ChunkType.TEXT, content=assistant_message.content)

                # Handle tool calls
                if not assistant_message.tool_calls:
                    break

                for tool_call in assistant_message.tool_calls:
                    func = tool_call.function

                    yield ResponseChunk(
                        type=ChunkType.TOOL_START,
                        tool_name=func.name,
                        tool_input=func.arguments,
                    )

                    # Execute tool
                    args = json.loads(func.arguments)
                    tool_result = await self._execute_tool(func.name, args)

                    yield ResponseChunk(
                        type=ChunkType.TOOL_END,
                        tool_name=func.name,
                        tool_output=tool_result,
                    )

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    })

        except Exception as e:
            logger.exception("OpenAI API error")
            yield ResponseChunk(type=ChunkType.ERROR, content=str(e))

    async def _process_mock(
        self,
        message: str,
        profile: str | None,
        space_id: str | None,
    ) -> AsyncIterator[ResponseChunk]:
        """
        Process without LLM - pattern matching for demo purposes.

        Used when no API keys are configured.
        """
        message_lower = message.lower()

        # Pattern: Create space
        if "create" in message_lower and "space" in message_lower:
            # Extract name from quotes or after "called"
            import re
            name_match = re.search(r'["\']([^"\']+)["\']|called\s+(\w+)', message)
            name = name_match.group(1) or name_match.group(2) if name_match else "New Space"

            yield ResponseChunk(
                type=ChunkType.TOOL_START,
                tool_name="create_space",
                tool_input=json.dumps({"name": name}),
            )

            result = await self._execute_tool("create_space", {"name": name})

            yield ResponseChunk(
                type=ChunkType.TOOL_END,
                tool_name="create_space",
                tool_output=result,
            )

            yield ResponseChunk(
                type=ChunkType.TEXT,
                content=f"I've created the space for you.\n\n{result}",
            )

        # Pattern: List spaces
        elif "list" in message_lower and "space" in message_lower:
            yield ResponseChunk(
                type=ChunkType.TOOL_START,
                tool_name="list_spaces",
                tool_input="{}",
            )

            result = await self._execute_tool("list_spaces", {})

            yield ResponseChunk(
                type=ChunkType.TOOL_END,
                tool_name="list_spaces",
                tool_output=result,
            )

            yield ResponseChunk(
                type=ChunkType.TEXT,
                content=f"Here are your spaces:\n\n{result}",
            )

        # Pattern: Search
        elif "search" in message_lower or "find" in message_lower:
            import re
            query_match = re.search(r'(?:search|find)\s+(?:for\s+)?["\']?([^"\']+)["\']?', message_lower)
            query = query_match.group(1).strip() if query_match else message

            yield ResponseChunk(
                type=ChunkType.TOOL_START,
                tool_name="search",
                tool_input=json.dumps({"query": query}),
            )

            result = await self._execute_tool("search", {"query": query})

            yield ResponseChunk(
                type=ChunkType.TOOL_END,
                tool_name="search",
                tool_output=result,
            )

            yield ResponseChunk(
                type=ChunkType.TEXT,
                content=f"Here's what I found:\n\n{result}",
            )

        # Pattern: Stats
        elif "stat" in message_lower or "graph" in message_lower or "overview" in message_lower:
            yield ResponseChunk(
                type=ChunkType.TOOL_START,
                tool_name="get_graph_stats",
                tool_input="{}",
            )

            result = await self._execute_tool("get_graph_stats", {})

            yield ResponseChunk(
                type=ChunkType.TOOL_END,
                tool_name="get_graph_stats",
                tool_output=result,
            )

            yield ResponseChunk(
                type=ChunkType.TEXT,
                content=f"Here's your knowledge graph overview:\n\n{result}",
            )

        # Pattern: Briefing
        elif "briefing" in message_lower or "summary" in message_lower or "recent" in message_lower:
            yield ResponseChunk(
                type=ChunkType.TOOL_START,
                tool_name="daily_briefing",
                tool_input="{}",
            )

            result = await self._execute_tool("daily_briefing", {})

            yield ResponseChunk(
                type=ChunkType.TOOL_END,
                tool_name="daily_briefing",
                tool_output=result,
            )

            yield ResponseChunk(
                type=ChunkType.TEXT,
                content=result,
            )

        # Default: Helpful response
        else:
            yield ResponseChunk(
                type=ChunkType.TEXT,
                content="""I can help you with:

- **Creating spaces**: "Create a space called 'Project Notes'"
- **Listing spaces**: "List my spaces"
- **Searching**: "Search for meeting notes"
- **Graph overview**: "Show me my graph stats"
- **Daily briefing**: "Give me a briefing"

What would you like to do?

*Note: For full conversational capabilities, configure ANTHROPIC_API_KEY or OPENAI_API_KEY.*
""",
            )

    async def _execute_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> str:
        """Execute a tool via the gateway API."""
        return await self._call_gateway_tool(tool_name, args)

    async def _call_gateway_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        profile: str | None = None,
    ) -> str:
        """Call a tool through the gateway REST API."""
        # Map tool names to API endpoints
        endpoint_map = {
            "switch_profile": ("POST", "/api/v1/profile/switch"),
            "create_space": ("POST", "/api/v1/spaces"),
            "list_spaces": ("GET", "/api/v1/spaces"),
            "create_object": ("POST", "/api/v1/objects"),
            "search": ("POST", "/api/v1/search"),
            "get_graph_stats": ("GET", "/api/v1/stats"),
            "ensure_ontology": ("POST", "/api/v1/ontology/ensure"),
            "smart_ingest": ("POST", "/api/v1/ingest"),
            "daily_briefing": ("GET", "/api/v1/briefing"),
        }

        if tool_name not in endpoint_map:
            return f"Unknown tool: {tool_name}"

        method, path = endpoint_map[tool_name]

        # Add profile to args if not present
        if profile and "profile_name" not in args:
            args["profile_name"] = profile

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(
                        f"{self.gateway_url}{path}",
                        params=args,
                    )
                else:
                    response = await client.post(
                        f"{self.gateway_url}{path}",
                        json=args,
                    )

                if response.status_code >= 400:
                    return f"Error: {response.status_code} - {response.text}"

                data = response.json()
                return json.dumps(data, indent=2)

        except httpx.ConnectError:
            return "Error: Cannot connect to gateway. Is penny-gateway running?"
        except Exception as e:
            logger.exception("Tool execution error")
            return f"Error: {str(e)}"
