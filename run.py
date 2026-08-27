"""Точка входа для запуска lk-tko-mcp как stdio MCP-сервера.

Именно этот файл регистрируется в Claude Code:
    claude mcp add lk-tko-mcp -- uv run run.py
"""

from server import mcp

if __name__ == "__main__":
    mcp.run()
