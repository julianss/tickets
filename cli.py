#!/usr/bin/env python3
"""
CLI for the ticket management system.
Usage: tickets <command> [options]
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

import db

console = Console()


def get_project() -> str:
    """Get the current project (working directory)."""
    return os.getcwd()


def format_status(status: str) -> Text:
    """Format status with color."""
    colors = {
        "pending": "yellow",
        "in_progress": "blue",
        "ready_to_test": "magenta",
        "closed": "green",
    }
    return Text(status, style=colors.get(status, "white"))


def format_priority(priority: str) -> Text:
    """Format priority with color."""
    colors = {
        "high": "red bold",
        "medium": "yellow",
        "low": "dim",
    }
    return Text(priority, style=colors.get(priority, "white"))


def format_tags(tags: str) -> Text:
    """Format tags."""
    if not tags:
        return Text("-", style="dim")
    return Text(tags, style="cyan")


@click.group()
def cli():
    """Mini JIRA - Ticket management for Claude Code."""
    pass


@cli.command("list")
@click.option("--status", "-s", type=click.Choice(["pending", "in_progress", "ready_to_test", "closed"]), help="Filter by status")
@click.option("--priority", "-p", type=click.Choice(["high", "medium", "low"]), help="Filter by priority")
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--all-projects", "-a", is_flag=True, help="Show tickets from all projects")
def list_tickets(status, priority, tag, all_projects):
    """List tickets for the current project."""
    project = None if all_projects else get_project()

    try:
        tickets = db.list_tickets(project=project, status=status, priority=priority, tag=tag)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if not tickets:
        console.print("[dim]No tickets found.[/dim]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Title", min_width=30)
    table.add_column("Status", width=14)
    table.add_column("Priority", width=8)
    table.add_column("Tags", width=15)

    if all_projects:
        table.add_column("Project", width=20)

    for ticket in tickets:
        row = [
            str(ticket["id"]),
            ticket["title"][:40] + ("..." if len(ticket["title"]) > 40 else ""),
            format_status(ticket["status"]),
            format_priority(ticket["priority"]),
            format_tags(ticket["tags"]),
        ]
        if all_projects:
            # Show just the last part of the project path
            project_name = os.path.basename(ticket["project"]) or ticket["project"]
            row.append(project_name)
        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(tickets)} ticket(s)[/dim]")


@cli.command("show")
@click.argument("ticket_id", type=int)
def show_ticket(ticket_id):
    """Show details of a specific ticket."""
    ticket = db.get_ticket(ticket_id)

    if not ticket:
        console.print(f"[red]Ticket #{ticket_id} not found.[/red]")
        sys.exit(1)

    # Header
    status_text = format_status(ticket["status"])
    priority_text = format_priority(ticket["priority"])

    header = Text()
    header.append(f"#{ticket['id']} ", style="cyan bold")
    header.append(ticket["title"], style="bold")

    console.print(Panel(header, box=box.ROUNDED))

    # Metadata
    meta_table = Table(show_header=False, box=None, padding=(0, 2))
    meta_table.add_column("Key", style="dim")
    meta_table.add_column("Value")

    meta_table.add_row("Status", status_text)
    meta_table.add_row("Priority", priority_text)
    meta_table.add_row("Tags", format_tags(ticket["tags"]))
    meta_table.add_row("Project", os.path.basename(ticket["project"]) or ticket["project"])
    meta_table.add_row("Created", ticket["created_at"][:19].replace("T", " "))
    meta_table.add_row("Updated", ticket["updated_at"][:19].replace("T", " "))

    console.print(meta_table)
    console.print()

    # Description
    console.print("[bold]Description:[/bold]")
    console.print(Panel(ticket["description"], box=box.SIMPLE))

    # Comments
    if ticket["comments"]:
        console.print(f"[bold]Comments ({len(ticket['comments'])}):[/bold]")
        for comment in ticket["comments"]:
            author_style = "green" if comment["author"] == "user" else "blue"
            console.print(f"  [{author_style}]{comment['author']}[/{author_style}] [dim]{comment['created_at'][:19].replace('T', ' ')}[/dim]")
            console.print(f"    {comment['content']}")
            console.print()
    else:
        console.print("[dim]No comments.[/dim]")


@cli.command("search")
@click.argument("query")
@click.option("--status", "-s", type=click.Choice(["pending", "in_progress", "ready_to_test", "closed"]), help="Filter by status")
@click.option("--all-projects", "-a", is_flag=True, help="Search across all projects")
def search_tickets(query, status, all_projects):
    """Search tickets by title, description, tags, and comments."""
    project = None if all_projects else get_project()

    try:
        tickets = db.search_tickets(query=query, project=project, status=status)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if not tickets:
        console.print(f"[dim]No tickets matching '{query}'.[/dim]")
        return

    table = Table(title=f"Search: '{query}'", box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Title", min_width=30)
    table.add_column("Status", width=14)
    table.add_column("Priority", width=8)
    table.add_column("Tags", width=15)

    if all_projects:
        table.add_column("Project", width=20)

    for ticket in tickets:
        row = [
            str(ticket["id"]),
            ticket["title"][:40] + ("..." if len(ticket["title"]) > 40 else ""),
            format_status(ticket["status"]),
            format_priority(ticket["priority"]),
            format_tags(ticket["tags"]),
        ]
        if all_projects:
            project_name = os.path.basename(ticket["project"]) or ticket["project"]
            row.append(project_name)
        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(tickets)} result(s)[/dim]")


@cli.command("create")
@click.argument("title")
@click.argument("description")
@click.option("--priority", "-p", type=click.Choice(["high", "medium", "low"]), default="medium", help="Ticket priority")
@click.option("--tags", "-t", default="", help="Comma-separated tags")
def create_ticket(title, description, priority, tags):
    """Create a new ticket."""
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
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    console.print(f"[green]Created ticket #{ticket['id']}:[/green] {ticket['title']}")


@cli.command("edit")
@click.argument("ticket_id", type=int)
@click.option("--title", "-t", help="New title")
@click.option("--description", "-d", help="New description")
@click.option("--priority", "-p", type=click.Choice(["high", "medium", "low"]), help="New priority")
@click.option("--tags", help="New tags (comma-separated)")
def edit_ticket(ticket_id, title, description, priority, tags):
    """Edit a ticket's fields."""
    if not any([title, description, priority, tags is not None]):
        console.print("[yellow]No changes specified.[/yellow]")
        return

    try:
        ticket = db.update_ticket(
            ticket_id=ticket_id,
            title=title,
            description=description,
            priority=priority,
            tags=tags
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if not ticket:
        console.print(f"[red]Ticket #{ticket_id} not found.[/red]")
        sys.exit(1)

    console.print(f"[green]Updated ticket #{ticket_id}.[/green]")


@cli.command("status")
@click.argument("ticket_id", type=int)
@click.argument("new_status", type=click.Choice(["pending", "in_progress", "ready_to_test", "closed"]))
def change_status(ticket_id, new_status):
    """Change a ticket's status."""
    ticket = db.update_ticket(ticket_id=ticket_id, status=new_status)

    if not ticket:
        console.print(f"[red]Ticket #{ticket_id} not found.[/red]")
        sys.exit(1)

    console.print(f"[green]Ticket #{ticket_id} status changed to[/green] ", end="")
    console.print(format_status(new_status))


@cli.command("delete")
@click.argument("ticket_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def delete_ticket(ticket_id, yes):
    """Delete a ticket and its comments."""
    ticket = db.get_ticket(ticket_id)

    if not ticket:
        console.print(f"[red]Ticket #{ticket_id} not found.[/red]")
        sys.exit(1)

    if not yes:
        console.print(f"[yellow]Delete ticket #{ticket_id}: {ticket['title']}?[/yellow]")
        if not click.confirm("Are you sure?"):
            console.print("[dim]Cancelled.[/dim]")
            return

    db.delete_ticket(ticket_id)
    console.print(f"[green]Deleted ticket #{ticket_id}.[/green]")


@cli.command("comment")
@click.argument("ticket_id", type=int)
@click.argument("message")
def add_comment(ticket_id, message):
    """Add a comment to a ticket."""
    comment = db.add_comment(ticket_id=ticket_id, author="user", content=message)

    if not comment:
        console.print(f"[red]Ticket #{ticket_id} not found.[/red]")
        sys.exit(1)

    console.print(f"[green]Added comment to ticket #{ticket_id}.[/green]")


if __name__ == "__main__":
    cli()
