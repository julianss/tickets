#!/usr/bin/env python3
"""
MCP Server for the ticket management system.
Exposes tools for Claude to interact with tickets.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

import db

# Create the MCP server
mcp = FastMCP("tickets")


def get_project() -> str:
    """Get the current project from environment or working directory."""
    # Claude Code sets CLAUDE_PROJECT_ROOT
    return os.environ.get("CLAUDE_PROJECT_ROOT", os.getcwd())


@mcp.tool()
def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    tag: str | None = None
) -> str:
    """
    List all tickets for the current project.

    Args:
        status: Filter by status (pending, in_progress, ready_to_test, closed)
        priority: Filter by priority (high, medium, low)
        tag: Filter by tag
    """
    project = get_project()

    try:
        tickets = db.list_tickets(project=project, status=status, priority=priority, tag=tag)
    except ValueError as e:
        return f"Error: {e}"

    if not tickets:
        return "No tickets found for this project."

    lines = [f"Found {len(tickets)} ticket(s):\n"]
    for t in tickets:
        tags_str = f" [{t['tags']}]" if t['tags'] else ""
        lines.append(f"#{t['id']} [{t['status']}] [{t['priority']}]{tags_str} {t['title']}")

    return "\n".join(lines)


@mcp.tool()
def get_ticket(ticket_id: int) -> str:
    """
    Get full details of a ticket including all comments.

    Args:
        ticket_id: The ID of the ticket to retrieve
    """
    ticket = db.get_ticket(ticket_id)

    if not ticket:
        return f"Ticket #{ticket_id} not found."

    lines = [
        f"Ticket #{ticket['id']}: {ticket['title']}",
        f"Status: {ticket['status']}",
        f"Priority: {ticket['priority']}",
        f"Tags: {ticket['tags'] or 'none'}",
        f"Project: {ticket['project']}",
        f"Created: {ticket['created_at']}",
        f"Updated: {ticket['updated_at']}",
        "",
        "Description:",
        ticket['description'],
    ]

    if ticket['comments']:
        lines.append("")
        lines.append(f"Comments ({len(ticket['comments'])}):")
        for c in ticket['comments']:
            lines.append(f"  [{c['author']}] {c['created_at'][:19]}: {c['content']}")

    return "\n".join(lines)


@mcp.tool()
def create_ticket(
    title: str,
    description: str,
    priority: str = "medium",
    tags: str = ""
) -> str:
    """
    Create a new ticket in the current project.

    Args:
        title: Short title for the ticket
        description: Full description of the work to be done
        priority: Priority level (high, medium, low). Default: medium
        tags: Comma-separated tags for categorization
    """
    project = get_project()

    try:
        ticket = db.create_ticket(
            project=project,
            title=title,
            description=description,
            priority=priority,
            tags=tags
        )
    except ValueError as e:
        return f"Error: {e}"

    return f"Created ticket #{ticket['id']}: {ticket['title']}"


@mcp.tool()
def update_ticket_status(ticket_id: int, status: str) -> str:
    """
    Update the status of a ticket. Use this when starting work, completing work, etc.

    Args:
        ticket_id: The ID of the ticket to update
        status: New status (pending, in_progress, ready_to_test, closed)
    """
    try:
        ticket = db.update_ticket(ticket_id=ticket_id, status=status)
    except ValueError as e:
        return f"Error: {e}"

    if not ticket:
        return f"Ticket #{ticket_id} not found."

    return f"Ticket #{ticket_id} status updated to: {status}"


@mcp.tool()
def add_comment(ticket_id: int, content: str) -> str:
    """
    Add a comment to a ticket. Use this to document progress, findings, or notes.

    Args:
        ticket_id: The ID of the ticket to comment on
        content: The comment text
    """
    comment = db.add_comment(ticket_id=ticket_id, author="claude", content=content)

    if not comment:
        return f"Ticket #{ticket_id} not found."

    return f"Added comment to ticket #{ticket_id}."


@mcp.tool()
def search_tickets(
    query: str,
    status: str | None = None,
) -> str:
    """
    Search tickets by matching a query against title, description, tags, and comments.

    Args:
        query: Text to search for across all ticket fields
        status: Optional status filter (pending, in_progress, ready_to_test, closed)
    """
    project = get_project()

    try:
        tickets = db.search_tickets(query=query, project=project, status=status)
    except ValueError as e:
        return f"Error: {e}"

    if not tickets:
        return f"No tickets matching '{query}'."

    lines = [f"Found {len(tickets)} ticket(s) matching '{query}':\n"]
    for t in tickets:
        tags_str = f" [{t['tags']}]" if t['tags'] else ""
        lines.append(f"#{t['id']} [{t['status']}] [{t['priority']}]{tags_str} {t['title']}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
