#!/bin/bash
# Stop All MCP Plugins

echo "Stopping all MCP plugins..."
echo "=================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANAGER_SCRIPT="$SCRIPT_DIR/mcp_manager.py"

if [ ! -f "$MANAGER_SCRIPT" ]; then
    echo "Error: $MANAGER_SCRIPT not found!"
    exit 1
fi

cd "$SCRIPT_DIR"
python "$MANAGER_SCRIPT" --stop-all