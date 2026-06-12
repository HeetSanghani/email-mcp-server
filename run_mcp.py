#!/usr/bin/env python3
"""
Email MCP Server — stdio Transport Entry Point
================================================
Starts the MCP server so it can be used by:
  • VS Code + Cline extension
  • VS Code + Continue.dev extension
  • VS Code + GitHub Copilot (agent mode)
  • MCP Inspector (for testing)
  • Any MCP-compatible client

This runs SEPARATELY from the web UI (uvicorn main:app).
Both can run at the same time — they are independent processes.

Usage:
    python run_mcp.py

Cline will start this automatically when you open VS Code.
Do NOT run this manually unless testing.
"""
import os
import sys
from pathlib import Path

# ── Ensure project root is on the Python path ──────────────────────────────
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# ── Change to project root so credentials/ paths resolve correctly ──────────
os.chdir(project_root)

# ── Load environment variables from .env ───────────────────────────────────
from dotenv import load_dotenv
load_dotenv(dotenv_path=project_root / ".env", override=True)

# ── Import the FastMCP server instance and run it ───────────────────────────
from mcp_server.server import mcp

if __name__ == "__main__":
    # stdio transport: Cline / VS Code starts this process and communicates
    # via stdin/stdout using the MCP JSON-RPC protocol.
    mcp.run()
