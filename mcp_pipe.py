"""
MCP Pipe - WebSocket to MCP Server Bridge
Version: 0.1.0

This script connects a WebSocket endpoint to an MCP server script with automatic reconnection.

Usage:
------
# Set environment variable
set MCP_ENDPOINT=<mcp_endpoint>  (Windows)
export MCP_ENDPOINT=<mcp_endpoint>  (Linux/Mac)

# Run MCP script from current directory
python mcp_pipe.py <mcp_script>

# Run MCP script from specific directory
python mcp_pipe.py <plugin_dir> <mcp_script>

Examples:
---------
python mcp_pipe.py calculator.py
python mcp_pipe.py ./calculator calculator.py
python mcp_pipe.py weather/weather.py

Environment Variables:
---------------------
MCP_ENDPOINT    WebSocket server URL (required)

"""

import asyncio
import websockets
import subprocess
import os
import signal
import sys
import random
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

# Configure loguru logger
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | MCP_PIPE | {message}", level="INFO")

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# Reconnection settings
INITIAL_BACKOFF = 1  # Initial wait time in seconds
MAX_BACKOFF = 600  # Maximum wait time in seconds
reconnect_attempt = 0
backoff = INITIAL_BACKOFF

async def connect_with_retry(uri):
    """Connect to WebSocket server with retry mechanism"""
    global reconnect_attempt, backoff
    while True:  # Infinite reconnection
        try:
            if reconnect_attempt > 0:
                wait_time = backoff * (1 + random.random() * 0.1)  # Add some random jitter
                logger.info(f"Reconnecting in {wait_time:.1f}s (attempt {reconnect_attempt})")
                await asyncio.sleep(wait_time)
                
            # Attempt to connect
            await connect_to_server(uri)
        
        except Exception as e:
            reconnect_attempt += 1
            logger.warning(f"Connection failed: {e}")            
            # Calculate wait time for next reconnection (exponential backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)

async def connect_to_server(uri):
    """Connect to WebSocket server and establish bidirectional communication with `mcp_script`"""
    global reconnect_attempt, backoff
    try:
        logger.info(f"Connecting to WebSocket...")
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected successfully")
            
            # Reset reconnection counter if connection closes normally
            reconnect_attempt = 0
            backoff = INITIAL_BACKOFF
            
            # Start mcp_script process
            if len(sys.argv) == 3:
                # Two arguments: plugin_dir and mcp_script
                plugin_dir = sys.argv[1]
                mcp_script = sys.argv[2]
                script_path = Path(plugin_dir) / mcp_script
                cwd = plugin_dir
            else:
                # Single argument: mcp_script (run in current directory)
                mcp_script = sys.argv[1]
                script_path = Path(mcp_script)
                cwd = None
            
            # Start process with unbuffered output to ensure real-time display
            process = subprocess.Popen(
                ['python', '-u', str(script_path)],  # -u for unbuffered output
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout to capture all output
                encoding='utf-8',
                text=True,
                cwd=cwd,
                bufsize=0,  # Unbuffered
                universal_newlines=True
            )
            logger.info(f"Started {mcp_script} (PID: {process.pid})")
            
            # Create tasks for bidirectional communication
            await asyncio.gather(
                pipe_websocket_to_process(websocket, process),
                pipe_process_to_websocket_and_terminal(process, websocket)
            )
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"Connection closed: {e}")
        raise  # Re-throw exception to trigger reconnection
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise  # Re-throw exception
    finally:
        # Ensure the child process is properly terminated
        if 'process' in locals():
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

async def pipe_websocket_to_process(websocket, process):
    """Read data from WebSocket and write to process stdin"""
    try:
        while True:
            # Read message from WebSocket
            message = await websocket.recv()
            
            # Write to process stdin (in text mode)
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            process.stdin.write(message + '\n')
            process.stdin.flush()
    except Exception as e:
        logger.error(f"WebSocket pipe error: {e}")
        raise  # Re-throw exception to trigger reconnection
    finally:
        # Close process stdin
        if not process.stdin.closed:
            process.stdin.close()

async def pipe_process_to_websocket_and_terminal(process, websocket):
    """Read data from process stdout and handle both WebSocket and terminal output"""
    try:
        while True:
            # Read data from process stdout (which now includes stderr)
            data = await asyncio.get_event_loop().run_in_executor(
                None, process.stdout.readline
            )
            
            if not data:  # If no data, the process may have ended
                break
                
            data_stripped = data.strip()
            
            # Check if this line is MCP protocol JSON (starts with { and contains jsonrpc)
            is_mcp_protocol = (data_stripped.startswith('{') and 
                             ('jsonrpc' in data_stripped or 'method' in data_stripped or 'result' in data_stripped))
            
            if is_mcp_protocol:
                # This is MCP protocol data, send to WebSocket only
                await websocket.send(data)
            else:
                # This is tool output (print, logger, etc.), display to terminal
                if data_stripped:  # Only display non-empty lines
                    # Print directly to terminal without additional formatting
                    print(data_stripped, flush=True)
                
                # Also check if we need to send this to WebSocket
                # (some tools might output non-JSON responses that should go to WebSocket)
                if any(keyword in data_stripped.lower() for keyword in ['error', 'result', 'response']):
                    await websocket.send(data)
                    
    except Exception as e:
        logger.error(f"Process output error: {e}")
        raise  # Re-throw exception to trigger reconnection

def sigint_handler(sig, frame):
    """Handle interrupt signals"""
    logger.info("Shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler
    signal.signal(signal.SIGINT, sigint_handler)
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        logger.error("Usage: python mcp_pipe.py <plugin_dir> <mcp_script> or python mcp_pipe.py <mcp_script>")
        sys.exit(1)
    
    # Get endpoint from environment variable
    endpoint_url = os.environ.get('MCP_ENDPOINT')
    if not endpoint_url:
        logger.error("Please set the `MCP_ENDPOINT` environment variable")
        sys.exit(1)
        
    # Start main loop
    try:
        asyncio.run(connect_with_retry(endpoint_url))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Execution error: {e}")