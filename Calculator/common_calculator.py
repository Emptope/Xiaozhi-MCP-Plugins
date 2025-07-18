from mcp.server.fastmcp import FastMCP
import sys
from loguru import logger
import math
import random

# Configure loguru logger to output to stderr
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | CommonCalculator | {message}", level="INFO")

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# Create an MCP server
mcp = FastMCP("CommonCalculator")

# Add calculator tool
@mcp.tool()
def common_calculate(python_expression: str) -> dict:
    """For mathematical calculation, always use this tool to calculate the result of a python expression. You can use 'math' or 'random' directly, without 'import'."""
    try:
        result = eval(python_expression, {"math": math, "random": random})
        
        # Only log the calculation result
        logger.info(f"Calculated: {python_expression} = {result}")
        
        return {"success": True, "result": result, "expression": python_expression}
        
    except Exception as e:
        error_msg = f"Calculation error: {str(e)}"
        logger.error(f"Error in '{python_expression}': {error_msg}")
        
        return {"success": False, "error": error_msg, "expression": python_expression}

# Start the server
if __name__ == "__main__":
    logger.info("Common Calculator MCP Server starting...")
    mcp.run(transport="stdio")
