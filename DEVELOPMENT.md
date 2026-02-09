# Tickets System - Development Notes

This document captures the design decisions and implementation details for future reference.

## Original Requirements

Create a plugin for Claude Code that acts like a mini JIRA:
- SQLite database to track tickets
- User can create tickets and tell Claude to work on them
- Claude can read tickets, understand what needs to be done
- Comments system (1 ticket : N comments)
- Both user and Claude can comment
- Claude updates ticket status, user acts as QA
- Workflow: Claude moves to "ready to test", user closes or returns to "in progress"
- CLI app for user CRUD operations

## Design Decisions

### Extension Mechanism: MCP Server

**Options considered:**
1. **Slash commands** - Simple markdown files, good for prompts but not for complex logic
2. **Skills** - Enhanced commands with frontmatter, can have supporting files
3. **MCP Server** - Exposes tools to Claude via Model Context Protocol
4. **Hooks** - Shell commands on lifecycle events

**Chosen: MCP Server** because:
- Claude gets structured tools to interact with the database
- Tools have proper input schemas and descriptions
- Can be combined with CLI sharing the same database layer
- Most flexible for this use case

### Storage: Global with Project Column

**Options considered:**
1. **Per-project** (`<project>/.claude/tickets/`) - Isolated but requires replicating code
2. **Global** (`~/.claude/tickets/`) - Centralized but no project separation
3. **Global with project column** - Best of both worlds

**Chosen: Global with project column** because:
- Single codebase to maintain - changes apply everywhere
- Tickets still scoped per project via `project` column
- Can query across all projects when needed (`--all-projects`)
- Project identified by current working directory

### Dependencies

**Chosen:** Full stack with virtual environment
- `mcp` - Official MCP SDK for Python
- `click` - CLI framework (better than argparse)
- `rich` - Pretty terminal output
- `textual` - TUI framework (built on rich)

**Virtual environment** solves the `externally-managed-environment` error on modern Python installations (PEP 668).

### Database Schema

Kept simple with two tables:

```sql
tickets (
    id INTEGER PRIMARY KEY,
    project TEXT,           -- Scoping
    title TEXT,
    description TEXT,
    status TEXT,            -- pending|in_progress|ready_to_test|closed
    priority TEXT,          -- high|medium|low
    tags TEXT,              -- Comma-separated for simplicity
    created_at TEXT,        -- ISO format
    updated_at TEXT
)

comments (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,      -- FK to tickets
    author TEXT,            -- "user" or "claude"
    content TEXT,
    created_at TEXT
)
```

**Why TEXT for dates?** SQLite doesn't have native datetime. ISO format strings sort correctly and are human-readable.

**Why comma-separated tags?** Simpler than a junction table. Good enough for this use case. Can query with `LIKE '%,tag,%'`.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ~/.claude/tickets/                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐          │
│   │ cli.py  │     │ tui.py  │     │mcp_server│          │
│   │ (user)  │     │ (user)  │     │ (claude) │          │
│   └────┬────┘     └────┬────┘     └────┬────┘          │
│        │               │               │                │
│        └───────────────┼───────────────┘                │
│                        ▼                                │
│                  ┌──────────┐                           │
│                  │  db.py   │                           │
│                  │ (shared) │                           │
│                  └────┬─────┘                           │
│                       ▼                                 │
│                ┌────────────┐                           │
│                │ tickets.db │                           │
│                │  (SQLite)  │                           │
│                └────────────┘                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

All three interfaces (CLI, TUI, MCP) share the same `db.py` layer.

## Implementation Details

### db.py
- Auto-initializes schema on import
- All functions are stateless (open/close connection per operation)
- Returns dicts (not Row objects) for JSON serialization
- `get_ticket()` includes comments in response

### cli.py
- Uses Click for command parsing
- Rich for colored output and tables
- Project = `os.getcwd()`
- Comments authored as "user"

### mcp_server.py
- Uses FastMCP from the `mcp` package
- Stdio transport (Claude Code spawns it)
- Project from `CLAUDE_PROJECT_ROOT` env var (falls back to cwd)
- Comments authored as "claude"
- Tools return plain text (not JSON) for readability

### tui.py
- Textual framework for full TUI
- Multiple screens: list, detail, create, edit, status, comment, delete
- Modal dialogs for forms
- Keyboard-driven navigation
- Real-time filtering by status/priority

### MCP Configuration

Added to `~/.claude.json`:
```json
{
  "mcpServers": {
    "tickets": {
      "type": "stdio",
      "command": "/home/user/.claude/tickets/.venv/bin/python",
      "args": ["/home/user/.claude/tickets/mcp_server.py"]
    }
  }
}
```

Claude Code auto-starts the server when needed.

## MCP Tools Exposed

| Tool | Parameters | Description |
|------|------------|-------------|
| `list_tickets` | status?, priority?, tag? | List project tickets |
| `get_ticket` | ticket_id | Get ticket + comments |
| `create_ticket` | title, description, priority?, tags? | Create ticket |
| `update_ticket_status` | ticket_id, status | Change status |
| `add_comment` | ticket_id, content | Add comment as claude |

## Future Enhancement Ideas

### Features
- [ ] Due dates / deadlines
- [ ] Time tracking (estimated vs actual)
- [ ] Subtasks / checklist items
- [ ] File attachments (store paths)
- [ ] Ticket templates
- [ ] Bulk operations in TUI
- [ ] Search across all fields
- [ ] Export to markdown/JSON

### Technical
- [ ] Add `update_ticket` MCP tool (for editing title/description)
- [ ] Add `delete_ticket` MCP tool (with confirmation prompt?)
- [ ] Webhook/hook integration on status changes
- [ ] Backup/restore commands
- [ ] Migration system for schema changes
- [ ] Tests

### UX
- [ ] Slash command `/ticket <id>` to quickly start work
- [ ] Auto-suggest ticket when Claude starts working on related code
- [ ] Integration with git commits (link commits to tickets)
- [ ] Notifications when ticket status changes

## Session Log

**2026-01-20** - Initial implementation
- Created db.py with full CRUD
- Created cli.py with Click + Rich
- Created mcp_server.py with FastMCP
- Created tui.py with Textual
- Configured MCP in ~/.claude.json
- Added priority and tags fields per user request
- Used global storage with project column per user request
- Fixed TUI escape key bug (missing action_pop_screen)
- Created 10 dummy tickets for testing
