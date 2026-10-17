# Supported hosts

This skill needs the **CapCut SFX Learning** local MCP tools. One installed service shares the same durable memory across hosts on this PC. Engine source is in the plugin package, not the skill-only ZIP. See the package's `INSTALL.md` for tested paths and commands.

- **Codex desktop:** install the local plugin marketplace, restart/open a fresh chat, then invoke this skill. The local MCP process reads saved drafts directly. CLI fallback: `<configured-python> <plugin-root>/cli.py <tool> --input <arguments.json>`; these arguments have the same names as MCP tools. Use this only when local shell access is available.
- **Claude Code:** copy this skill into `~/.claude/skills/capcut-sfx-learning`, connect the local stdio MCP server with `claude mcp add --scope user --transport stdio capcut-sfx-learning -- <python> <plugin-root>/launch.py`, then start a fresh session.
- **Claude Desktop:** add the provided named `mcpServers` entry to the existing Desktop config, preserving other servers. Enable/upload this skill or give its instructions to Claude. Restart and check tool availability; configuration alone does not prove a connected session.
- **ChatGPT web:** a skill/plugin archive alone has no Windows file access. Connect the local service through the account's supported **Secure MCP Tunnel**, or an authenticated reachable remote MCP endpoint. The package supplies an optional loopback HTTP server at `127.0.0.1:8776/mcp` for a supported tunnel. Do not expose it publicly without authentication. Account availability and connection are user setup steps; this build has not connected a ChatGPT web account.
- **Claude web:** skill upload loads instructions, not a local stdio process. Use a supported remote connector for live local work, or upload prepared context and return a plan to the local CLI. Do not pretend cloud sandbox paths are this PC.

Same engine/data/schema run across hosts; creative model choices can differ. Cross-host artistic equivalence has not been measured.
