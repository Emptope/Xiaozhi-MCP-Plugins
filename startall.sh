#!/bin/bash
# Start All MCP Plugins - Shell Script
# Compatible with Git Bash, WSL, and other Unix-like shells on Windows

echo "Starting all MCP plugins..."
echo "=================================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANAGER_SCRIPT="$SCRIPT_DIR/mcp_manager.py"

# Check if manager script exists
if [ ! -f "$MANAGER_SCRIPT" ]; then
    echo "Error: $MANAGER_SCRIPT not found!"
    exit 1
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "Error: Python is not installed or not in PATH!"
    exit 1
fi

# Check if MCP_ENDPOINT is set
if [ -z "$MCP_ENDPOINT" ]; then
    echo "Warning: MCP_ENDPOINT environment variable is not set!"
    echo "Please set it using: export MCP_ENDPOINT=your_websocket_endpoint"
fi

echo "Using manager script: $MANAGER_SCRIPT"
echo "Current directory: $SCRIPT_DIR"
echo ""

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down all plugins..."
    python "$MANAGER_SCRIPT" --stop-all
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start all plugins
echo "Executing: python $MANAGER_SCRIPT --all"
echo ""

cd "$SCRIPT_DIR"
python "$MANAGER_SCRIPT" --all