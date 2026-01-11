"""
PENNY Knowledge Core - Chainlit Application

The main chat interface for interacting with the knowledge graph.
Provides a conversational UI with tool execution visualization.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import chainlit as cl
from chainlit.input_widget import Select, TextInput

from penny_knowledge_core.config import get_settings
from penny_knowledge_core.logging import configure_logging, get_logger
from penny_knowledge_core.ui.agent import PennyAgent
from penny_knowledge_core.ui.handlers import handle_file_upload

logger = get_logger(__name__)

# =============================================================================
# Session State Keys
# =============================================================================

SESSION_PROFILE = "profile"
SESSION_SPACE_ID = "space_id"
SESSION_AGENT = "agent"


# =============================================================================
# Lifecycle Hooks
# =============================================================================


@cl.on_chat_start
async def on_chat_start() -> None:
    """
    Initialize the chat session.

    Sets up the agent, profile selector, and welcome message.
    """
    configure_logging()
    settings = get_settings()

    # Initialize session state
    cl.user_session.set(SESSION_PROFILE, settings.default_profile)
    cl.user_session.set(SESSION_SPACE_ID, None)

    # Create the agent
    agent = PennyAgent()
    cl.user_session.set(SESSION_AGENT, agent)

    # Set up chat settings (profile selector)
    await setup_chat_settings()

    # Send welcome message
    profile = cl.user_session.get(SESSION_PROFILE)
    await cl.Message(
        content=f"""# Welcome to PENNY

I'm your intelligent knowledge concierge. I can help you:

- **Create and organize spaces** for different projects
- **Design schemas** with custom Types and Relations
- **Ingest content** from text, URLs, or files
- **Search** across your knowledge graph
- **Generate briefings** of recent activity

**Current Profile:** `{profile}`

---

*Try asking:* "Create a new space called 'Research Notes'" or "What's in my knowledge graph?"
""",
        author="PENNY",
    ).send()


@cl.on_settings_update
async def on_settings_update(settings: dict[str, Any]) -> None:
    """Handle settings updates from the UI."""
    new_profile = settings.get("profile")
    if new_profile:
        old_profile = cl.user_session.get(SESSION_PROFILE)
        cl.user_session.set(SESSION_PROFILE, new_profile)

        if old_profile != new_profile:
            await cl.Message(
                content=f"Switched profile: `{old_profile}` → `{new_profile}`",
                author="System",
            ).send()

    new_space = settings.get("space_id")
    if new_space:
        cl.user_session.set(SESSION_SPACE_ID, new_space)


async def setup_chat_settings() -> None:
    """Configure the chat settings panel."""
    settings = get_settings()
    fleet_config = settings.get_fleet_config()

    profile_options = [name.capitalize() for name in fleet_config.keys()]

    await cl.ChatSettings(
        [
            Select(
                id="profile",
                label="Active Profile",
                description="Select your identity context",
                values=profile_options,
                initial_value=settings.default_profile.capitalize(),
            ),
            TextInput(
                id="space_id",
                label="Default Space ID",
                description="Set a default space for operations (optional)",
                placeholder="Enter space ID...",
            ),
        ]
    ).send()


# =============================================================================
# Message Handling
# =============================================================================


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """
    Handle incoming user messages.

    Routes the message to the agent for processing and streams
    the response with tool execution visualization.
    """
    agent: PennyAgent = cl.user_session.get(SESSION_AGENT)
    profile = cl.user_session.get(SESSION_PROFILE)
    space_id = cl.user_session.get(SESSION_SPACE_ID)

    # Handle file attachments
    if message.elements:
        await handle_file_upload(message.elements, profile, space_id)
        return

    # Process the message through the agent
    response_msg = cl.Message(content="", author="PENNY")
    await response_msg.send()

    try:
        # Stream the response
        async for chunk in agent.process_message(
            message.content,
            profile=profile,
            space_id=space_id,
        ):
            if chunk.type == "text":
                await response_msg.stream_token(chunk.content)
            elif chunk.type == "tool_start":
                # Show tool execution step
                step = cl.Step(
                    name=chunk.tool_name,
                    type="tool",
                    show_input=True,
                )
                step.input = chunk.tool_input
                await step.send()
                cl.user_session.set(f"step_{chunk.tool_name}", step)
            elif chunk.type == "tool_end":
                # Complete tool execution step
                step = cl.user_session.get(f"step_{chunk.tool_name}")
                if step:
                    step.output = chunk.tool_output
                    await step.update()
            elif chunk.type == "error":
                await response_msg.stream_token(f"\n\n**Error:** {chunk.content}")

        await response_msg.update()

    except Exception as e:
        logger.exception("Error processing message")
        await response_msg.stream_token(f"\n\nI encountered an error: {str(e)}")
        await response_msg.update()


# =============================================================================
# Action Handlers
# =============================================================================


@cl.action_callback("create_space")
async def on_create_space(action: cl.Action) -> None:
    """Handle create space action button."""
    await cl.Message(
        content="Let's create a new space. What would you like to call it?",
        author="PENNY",
    ).send()


@cl.action_callback("search")
async def on_search(action: cl.Action) -> None:
    """Handle search action button."""
    await cl.Message(
        content="What would you like to search for?",
        author="PENNY",
    ).send()


@cl.action_callback("daily_briefing")
async def on_daily_briefing(action: cl.Action) -> None:
    """Handle daily briefing action button."""
    agent: PennyAgent = cl.user_session.get(SESSION_AGENT)
    profile = cl.user_session.get(SESSION_PROFILE)

    msg = cl.Message(content="", author="PENNY")
    await msg.send()

    async for chunk in agent.generate_briefing(profile=profile):
        await msg.stream_token(chunk.content)

    await msg.update()


# =============================================================================
# Entry Point
# =============================================================================


def main() -> None:
    """Run the Chainlit application."""
    configure_logging()

    # Get the path to the chainlit config
    config_path = Path(__file__).parent.parent.parent.parent / ".chainlit" / "config.toml"
    app_path = Path(__file__)

    # Run chainlit
    cmd = [
        sys.executable, "-m", "chainlit", "run",
        str(app_path),
        "--host", os.getenv("UI_HOST", "0.0.0.0"),
        "--port", os.getenv("UI_PORT", "8080"),
    ]

    if os.getenv("DEBUG", "false").lower() == "true":
        cmd.append("--watch")

    subprocess.run(cmd)


if __name__ == "__main__":
    main()
