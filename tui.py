#!/usr/bin/env python3
"""
Terminal UI for the ticket management system.
A full CRUD interface using Textual.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TextArea,
)

import db


def get_project() -> str:
    """Get the current project (working directory)."""
    return os.getcwd()


# ============ Screens ============


class TicketDetailScreen(Screen):
    """Screen showing ticket details."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("e", "edit", "Edit"),
        Binding("s", "change_status", "Status"),
        Binding("c", "add_comment", "Comment"),
        Binding("d", "delete", "Delete"),
    ]

    def __init__(self, ticket_id: int):
        super().__init__()
        self.ticket_id = ticket_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="detail-container")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_ticket()

    def refresh_ticket(self) -> None:
        ticket = db.get_ticket(self.ticket_id)
        container = self.query_one("#detail-container")
        container.remove_children()

        if not ticket:
            container.mount(Static("[red]Ticket not found.[/red]"))
            return

        # Status colors
        status_colors = {
            "pending": "yellow",
            "in_progress": "blue",
            "ready_to_test": "magenta",
            "closed": "green",
        }
        priority_colors = {"high": "red bold", "medium": "yellow", "low": "dim"}

        status_color = status_colors.get(ticket["status"], "white")
        priority_color = priority_colors.get(ticket["priority"], "white")

        content = f"""[bold cyan]#{ticket['id']}[/bold cyan] [bold]{ticket['title']}[/bold]

[dim]Status:[/dim]   [{status_color}]{ticket['status']}[/{status_color}]
[dim]Priority:[/dim] [{priority_color}]{ticket['priority']}[/{priority_color}]
[dim]Tags:[/dim]     [cyan]{ticket['tags'] or '-'}[/cyan]
[dim]Project:[/dim]  {os.path.basename(ticket['project']) or ticket['project']}
[dim]Created:[/dim]  {ticket['created_at'][:19].replace('T', ' ')}
[dim]Updated:[/dim]  {ticket['updated_at'][:19].replace('T', ' ')}

[bold]Description:[/bold]
{ticket['description']}

[bold]Comments ({len(ticket['comments'])}):[/bold]
"""
        for c in ticket["comments"]:
            author_color = "green" if c["author"] == "user" else "blue"
            content += f"\n[{author_color}]{c['author']}[/{author_color}] [dim]{c['created_at'][:19].replace('T', ' ')}[/dim]\n  {c['content']}\n"

        if not ticket["comments"]:
            content += "\n[dim]No comments yet.[/dim]"

        container.mount(Static(content, markup=True))

    def action_pop_screen(self) -> None:
        self.app.pop_screen()

    def action_edit(self) -> None:
        ticket = db.get_ticket(self.ticket_id)
        if ticket:
            self.app.push_screen(EditTicketScreen(ticket), self._on_edit_done)

    def _on_edit_done(self, updated: bool) -> None:
        if updated:
            self.refresh_ticket()

    def action_change_status(self) -> None:
        self.app.push_screen(ChangeStatusScreen(self.ticket_id), self._on_status_done)

    def _on_status_done(self, updated: bool) -> None:
        if updated:
            self.refresh_ticket()

    def action_add_comment(self) -> None:
        self.app.push_screen(AddCommentScreen(self.ticket_id), self._on_comment_done)

    def _on_comment_done(self, added: bool) -> None:
        if added:
            self.refresh_ticket()

    def action_delete(self) -> None:
        self.app.push_screen(ConfirmDeleteScreen(self.ticket_id), self._on_delete_done)

    def _on_delete_done(self, deleted: bool) -> None:
        if deleted:
            self.app.pop_screen()


class CreateTicketScreen(ModalScreen[bool]):
    """Modal screen for creating a new ticket."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold]Create New Ticket[/bold]\n", id="modal-title"),
            Label("Title:"),
            Input(placeholder="Short title", id="title-input"),
            Label("Description:"),
            TextArea(id="desc-input"),
            Label("Priority:"),
            Select(
                [(p, p) for p in ["medium", "high", "low"]],
                value="medium",
                id="priority-select",
            ),
            Label("Tags (comma-separated):"),
            Input(placeholder="tag1,tag2", id="tags-input"),
            Horizontal(
                Button("Create", variant="primary", id="create-btn"),
                Button("Cancel", variant="default", id="cancel-btn"),
                id="button-row",
            ),
            id="modal-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-btn":
            title = self.query_one("#title-input", Input).value.strip()
            desc = self.query_one("#desc-input", TextArea).text.strip()
            priority = self.query_one("#priority-select", Select).value
            tags = self.query_one("#tags-input", Input).value.strip()

            if not title:
                self.notify("Title is required", severity="error")
                return
            if not desc:
                self.notify("Description is required", severity="error")
                return

            try:
                db.create_ticket(
                    project=get_project(),
                    title=title,
                    description=desc,
                    priority=priority,
                    tags=tags,
                )
                self.dismiss(True)
            except ValueError as e:
                self.notify(str(e), severity="error")
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class EditTicketScreen(ModalScreen[bool]):
    """Modal screen for editing a ticket."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, ticket: dict):
        super().__init__()
        self.ticket = ticket

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[bold]Edit Ticket #{self.ticket['id']}[/bold]\n", id="modal-title"),
            Label("Title:"),
            Input(value=self.ticket["title"], id="title-input"),
            Label("Description:"),
            TextArea(self.ticket["description"], id="desc-input"),
            Label("Priority:"),
            Select(
                [(p, p) for p in ["high", "medium", "low"]],
                value=self.ticket["priority"],
                id="priority-select",
            ),
            Label("Tags (comma-separated):"),
            Input(value=self.ticket["tags"], id="tags-input"),
            Horizontal(
                Button("Save", variant="primary", id="save-btn"),
                Button("Cancel", variant="default", id="cancel-btn"),
                id="button-row",
            ),
            id="modal-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            title = self.query_one("#title-input", Input).value.strip()
            desc = self.query_one("#desc-input", TextArea).text.strip()
            priority = self.query_one("#priority-select", Select).value
            tags = self.query_one("#tags-input", Input).value.strip()

            if not title:
                self.notify("Title is required", severity="error")
                return

            try:
                db.update_ticket(
                    ticket_id=self.ticket["id"],
                    title=title,
                    description=desc,
                    priority=priority,
                    tags=tags,
                )
                self.dismiss(True)
            except ValueError as e:
                self.notify(str(e), severity="error")
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class ChangeStatusScreen(ModalScreen[bool]):
    """Modal screen for changing ticket status."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, ticket_id: int):
        super().__init__()
        self.ticket_id = ticket_id

    def compose(self) -> ComposeResult:
        ticket = db.get_ticket(self.ticket_id)
        current = ticket["status"] if ticket else "pending"

        yield Container(
            Static("[bold]Change Status[/bold]\n", id="modal-title"),
            Label(f"Current: [bold]{current}[/bold]"),
            Label("\nNew status:"),
            Select(
                [(s, s) for s in ["pending", "in_progress", "ready_to_test", "closed"]],
                value=current,
                id="status-select",
            ),
            Horizontal(
                Button("Update", variant="primary", id="update-btn"),
                Button("Cancel", variant="default", id="cancel-btn"),
                id="button-row",
            ),
            id="modal-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "update-btn":
            status = self.query_one("#status-select", Select).value
            db.update_ticket(self.ticket_id, status=status)
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class AddCommentScreen(ModalScreen[bool]):
    """Modal screen for adding a comment."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, ticket_id: int):
        super().__init__()
        self.ticket_id = ticket_id

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold]Add Comment[/bold]\n", id="modal-title"),
            Label("Comment:"),
            TextArea(id="comment-input"),
            Horizontal(
                Button("Add", variant="primary", id="add-btn"),
                Button("Cancel", variant="default", id="cancel-btn"),
                id="button-row",
            ),
            id="modal-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            content = self.query_one("#comment-input", TextArea).text.strip()
            if not content:
                self.notify("Comment cannot be empty", severity="error")
                return
            db.add_comment(self.ticket_id, author="user", content=content)
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class SearchScreen(ModalScreen[str]):
    """Modal screen for entering a search query."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold]Search Tickets[/bold]\n", id="modal-title"),
            Label("Search across titles, descriptions, tags, and comments:"),
            Input(placeholder="Search query...", id="search-input"),
            Horizontal(
                Button("Search", variant="primary", id="search-btn"),
                Button("Cancel", variant="default", id="cancel-btn"),
                id="button-row",
            ),
            id="modal-container",
        )

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-btn":
            query = self.query_one("#search-input", Input).value.strip()
            if not query:
                self.notify("Enter a search query", severity="error")
                return
            self.dismiss(query)
        else:
            self.dismiss("")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.dismiss(query)

    def action_cancel(self) -> None:
        self.dismiss("")


class ConfirmDeleteScreen(ModalScreen[bool]):
    """Modal screen for confirming deletion."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, ticket_id: int):
        super().__init__()
        self.ticket_id = ticket_id

    def compose(self) -> ComposeResult:
        ticket = db.get_ticket(self.ticket_id)
        title = ticket["title"] if ticket else "Unknown"

        yield Container(
            Static("[bold red]Delete Ticket?[/bold red]\n", id="modal-title"),
            Static(f"Are you sure you want to delete:\n[bold]#{self.ticket_id}: {title}[/bold]\n\nThis cannot be undone."),
            Horizontal(
                Button("Delete", variant="error", id="delete-btn"),
                Button("Cancel", variant="default", id="cancel-btn"),
                id="button-row",
            ),
            id="modal-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete-btn":
            db.delete_ticket(self.ticket_id)
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


# ============ Main App ============


class TicketApp(App):
    """Main ticket management TUI application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #ticket-table {
        height: 100%;
    }

    #modal-container {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #modal-title {
        text-align: center;
        padding-bottom: 1;
    }

    #button-row {
        margin-top: 1;
        align: center middle;
    }

    #button-row Button {
        margin: 0 1;
    }

    #desc-input, #comment-input {
        height: 6;
    }

    Label {
        margin-top: 1;
    }

    #filter-bar {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
    }

    #filter-bar Select {
        width: 20;
        margin-right: 2;
    }

    #detail-container {
        padding: 1 2;
    }

    ConfirmDeleteScreen #modal-container {
        height: auto;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("n", "new_ticket", "New"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "toggle_all_projects", "All Projects"),
        Binding("slash", "search", "Search"),
        Binding("escape", "clear_search", "Clear Search"),
        Binding("enter", "view_ticket", "View"),
    ]

    def __init__(self):
        super().__init__()
        self.show_all_projects = False
        self.search_query: str = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Select(
                [("All", None), ("pending", "pending"), ("in_progress", "in_progress"), ("ready_to_test", "ready_to_test"), ("closed", "closed")],
                value=None,
                prompt="Status",
                id="status-filter",
            ),
            Select(
                [("All", None), ("high", "high"), ("medium", "medium"), ("low", "low")],
                value=None,
                prompt="Priority",
                id="priority-filter",
            ),
            Static("", id="project-indicator"),
            id="filter-bar",
        )
        yield DataTable(id="ticket-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#ticket-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("ID", "Title", "Status", "Priority", "Tags", "Updated")
        self.refresh_tickets()

    def refresh_tickets(self) -> None:
        table = self.query_one("#ticket-table", DataTable)
        table.clear()

        status_filter = self.query_one("#status-filter", Select).value
        priority_filter = self.query_one("#priority-filter", Select).value
        project = None if self.show_all_projects else get_project()

        # Update project indicator
        indicator = self.query_one("#project-indicator", Static)
        if self.search_query:
            indicator.update(f"[bold yellow]Search: '{self.search_query}'[/bold yellow]  [dim](Esc to clear)[/dim]")
        elif self.show_all_projects:
            indicator.update("[cyan]Showing all projects[/cyan]")
        else:
            indicator.update(f"[dim]Project: {os.path.basename(project) or project}[/dim]")

        if self.search_query:
            tickets = db.search_tickets(
                query=self.search_query,
                project=project,
                status=status_filter if status_filter else None,
            )
        else:
            tickets = db.list_tickets(
                project=project,
                status=status_filter if status_filter else None,
                priority=priority_filter if priority_filter else None,
            )

        for t in tickets:
            status_colors = {
                "pending": "yellow",
                "in_progress": "blue",
                "ready_to_test": "magenta",
                "closed": "green",
            }
            priority_colors = {"high": "red", "medium": "yellow", "low": "dim"}

            status_color = status_colors.get(t["status"], "white")
            priority_color = priority_colors.get(t["priority"], "white")

            table.add_row(
                str(t["id"]),
                t["title"][:35] + ("..." if len(t["title"]) > 35 else ""),
                f"[{status_color}]{t['status']}[/{status_color}]",
                f"[{priority_color}]{t['priority']}[/{priority_color}]",
                t["tags"] or "-",
                t["updated_at"][:10],
                key=str(t["id"]),
            )

        self.sub_title = f"{len(tickets)} ticket(s)"

    def on_select_changed(self, event: Select.Changed) -> None:
        self.refresh_tickets()

    def action_refresh(self) -> None:
        self.refresh_tickets()
        self.notify("Refreshed")

    def action_toggle_all_projects(self) -> None:
        self.show_all_projects = not self.show_all_projects
        self.refresh_tickets()

    def action_search(self) -> None:
        self.push_screen(SearchScreen(), self._on_search_done)

    def _on_search_done(self, query: str) -> None:
        self.search_query = query
        self.refresh_tickets()
        if query:
            self.notify(f"Searching: '{query}'")

    def action_clear_search(self) -> None:
        if self.search_query:
            self.search_query = ""
            self.refresh_tickets()
            self.notify("Search cleared")

    def action_new_ticket(self) -> None:
        self.push_screen(CreateTicketScreen(), self._on_ticket_created)

    def _on_ticket_created(self, created: bool) -> None:
        if created:
            self.refresh_tickets()
            self.notify("Ticket created")

    def action_view_ticket(self) -> None:
        table = self.query_one("#ticket-table", DataTable)
        if table.row_count == 0:
            return

        row_key = table.cursor_row
        if row_key is not None:
            ticket_id = int(table.get_row_at(row_key)[0])
            self.push_screen(TicketDetailScreen(ticket_id), self._on_detail_closed)

    def _on_detail_closed(self, _: None) -> None:
        self.refresh_tickets()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        ticket_id = int(event.data_table.get_row(event.row_key)[0])
        self.push_screen(TicketDetailScreen(ticket_id), self._on_detail_closed)


def main():
    app = TicketApp()
    app.title = "Tickets"
    app.run()


if __name__ == "__main__":
    main()
