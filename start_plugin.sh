#!/bin/bash
# Start Specific MCP Plugin

if [ $# -eq 0 ]; then
    echo "Usage: $0 <plugin_name>"
    echo "Example: $0 calculator"
    exit 1
fi

PLUGIN_NAME="$1"
echo "Starting MCP plugin: $PLUGIN_NAME"
echo "=================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANAGER_SCRIPT="$SCRIPT_DIR/mcp_manager.py"

if [ ! -f "$MANAGER_SCRIPT" ]; then
    echo "Error: $MANAGER_SCRIPT not found!"
    exit 1
fi

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "Stopping plugin: $PLUGIN_NAME"
    python "$MANAGER_SCRIPT" --stop "$PLUGIN_NAME"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

cd "$SCRIPT_DIR"
python "$MANAGER_SCRIPT" --plugin "$PLUGIN_NAME"