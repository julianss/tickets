# Tickets - Mini JIRA for Claude Code

A lightweight ticket management system that integrates with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) via MCP. Track tasks, bugs, and features with a shared workflow between you and Claude.

## Installation

### 1. Clone into your Claude config directory

```bash
git clone https://github.com/YOURUSERNAME/claude-tickets ~/.claude/tickets
```

### 2. Create a virtual environment and install dependencies

```bash
cd ~/.claude/tickets
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Configure the MCP server

Add the following to your `~/.claude.json` (create the file if it doesn't exist). Replace `USER` with your system username:

```json
{
  "mcpServers": {
    "tickets": {
      "type": "stdio",
      "command": "/home/USER/.claude/tickets/.venv/bin/python",
      "args": ["/home/USER/.claude/tickets/mcp_server.py"]
    }
  }
}
```

> **Tip:** Run `echo $HOME` to get your home directory path, then substitute it in the config above.

If `~/.claude.json` already exists with other MCP servers, just add the `"tickets"` entry inside the existing `"mcpServers"` object.

### 4. Shell aliases (optional, for CLI/TUI)

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias tickets='~/.claude/tickets/.venv/bin/python ~/.claude/tickets/cli.py'
alias tickets-ui='~/.claude/tickets/.venv/bin/python ~/.claude/tickets/tui.py'
```

Then reload: `source ~/.bashrc` (or `source ~/.zshrc`)

### 5. Restart Claude Code

Claude Code reads MCP config on startup. After configuring, restart it so Claude picks up the ticket tools.

## How it works

The ticket system gives Claude access to these MCP tools:

| Tool | Description |
|------|-------------|
| `list_tickets` | List tickets for the current project |
| `get_ticket` | Read ticket details and comments |
| `create_ticket` | Create new tickets |
| `update_ticket_status` | Change ticket status |
| `add_comment` | Add comments to tickets |
| `search_tickets` | Search across all ticket fields |

Tickets are **scoped by project** (your current working directory), so each project gets its own set of tickets while sharing a single database.

## Usage

### With Claude

Just talk to Claude naturally:

```
"Create a ticket for implementing user authentication"
"Work on ticket #3"
"What tickets are pending?"
"Mark ticket #5 as ready to test"
```

### CLI

```bash
# List tickets (current project)
tickets list
tickets list --status pending
tickets list --priority high
tickets list --all-projects        # Show all projects

# View ticket details
tickets show 1

# Create ticket
tickets create "Title" "Description"
tickets create "Bug fix" "Details..." --priority high --tags "bug,urgent"

# Edit ticket
tickets edit 1 --title "New title"
tickets edit 1 --priority low --tags "feature"

# Change status
tickets status 1 in_progress
tickets status 1 ready_to_test
tickets status 1 closed

# Add comment
tickets comment 1 "This is my feedback"

# Delete ticket
tickets delete 1
tickets delete 1 --yes             # Skip confirmation
```

### Terminal UI


<img width="930" height="501" alt="Captura de pantalla 2026-02-09 123621" src="https://github.com/user-attachments/assets/54517853-6ca3-4b5c-a098-e4a56db53d8f" />


Launch the interactive TUI:

```bash
tickets-ui
```

**Main List Shortcuts:**
| Key | Action |
|-----|--------|
| `n` | Create new ticket |
| `Enter` | View ticket details |
| `r` | Refresh list |
| `a` | Toggle all projects / current project |
| `q` | Quit |

**Ticket Detail Shortcuts:**
| Key | Action |
|-----|--------|
| `e` | Edit ticket |
| `s` | Change status |
| `c` | Add comment |
| `d` | Delete ticket |
| `Escape` | Back to list |

## Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   pending   │ ──► │ in_progress │ ──► │ready_to_test│ ──► │   closed    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     You                Claude              You (QA)            Done!
   creates            works on it         tests & approves
                                                │
                                                ▼
                                          ┌─────────────┐
                                          │  rejected?  │
                                          │  back to    │
                                          │ in_progress │
                                          └─────────────┘
```

1. **You** create a ticket via CLI, TUI, or ask Claude
2. **You** tell Claude: "work on ticket #X"
3. **Claude** reads the ticket, implements it, adds progress comments
4. **Claude** marks it `ready_to_test` when done
5. **You** test the implementation
6. **You** either close it or send it back to `in_progress` with feedback

## Architecture

```
~/.claude/tickets/
├── requirements.txt # Python dependencies
├── db.py            # Database layer (SQLite)
├── cli.py           # Command-line interface (Click + Rich)
├── mcp_server.py    # MCP server for Claude
├── tui.py           # Terminal UI (Textual)
└── tickets.db       # SQLite database (created on first run)
```

All three interfaces (CLI, TUI, MCP) share the same `db.py` layer and `tickets.db` database.

## Troubleshooting

**Claude doesn't have ticket tools:**
- Restart Claude Code after adding the MCP config
- Verify `~/.claude.json` has the `mcpServers.tickets` entry
- Check that the paths in the config point to the actual venv python and `mcp_server.py`

**"No tickets found" but tickets exist:**
- Tickets are project-scoped by working directory. Use `--all-projects` (CLI) or `a` key (TUI) to see all
- Make sure you're in the same directory where the tickets were created

**Import errors when running the MCP server:**
- Make sure you ran `pip install -r requirements.txt` inside the `.venv`
- The config in `~/.claude.json` must point to `.venv/bin/python`, not your system python

## Requirements

- Python 3.10+
- Claude Code
