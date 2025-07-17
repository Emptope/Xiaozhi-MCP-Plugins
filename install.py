#!/usr/bin/env python3
"""
MCP Plugin Collection Installation Script
"""

import subprocess
import sys
import os
from pathlib import Path
from loguru import logger

# Configure loguru logger
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="INFO")

def install_requirements():
    """Install dependencies from root requirements.txt"""
    workspace = Path(__file__).parent
    requirements_file = workspace / "requirements.txt"
    
    logger.info("Starting MCP plugin dependencies installation...")
    
    if not requirements_file.exists():
        logger.error("requirements.txt not found in root directory")
        return False
    
    try:
        logger.info("Installing dependencies from requirements.txt...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True, capture_output=True, text=True)
        
        logger.info("All dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Dependencies installation failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error during installation: {e}")
        return False

def check_environment():
    """Check environment configuration"""
    env_file = Path(__file__).parent / ".env"
    
    if not env_file.exists():
        logger.warning(".env file not found, please create and configure necessary environment variables")
        return False
    
    # Check required environment variables
    required_vars = ["MCP_ENDPOINT"]
    missing_vars = []
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for var in required_vars:
                if var not in content:
                    missing_vars.append(var)
    except Exception as e:
        logger.error(f"Error reading .env file: {e}")
        return False
    
    if missing_vars:
        logger.warning(f"Missing environment variables in .env file: {', '.join(missing_vars)}")
        return False
    
    logger.info("Environment configuration check passed")
    return True

def show_usage():
    """Show usage instructions"""
    logger.info("\nUsage instructions:")
    logger.info("  python mcp_manager.py --list     # List all plugins")
    logger.info("  python mcp_manager.py --all      # Start all plugins")
    logger.info("  start_mcp.bat all               # Windows batch startup")

if __name__ == "__main__":
    logger.info("MCP Plugin Collection Installation Program")
    logger.info("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 7):
        logger.error("Python 3.7 or higher is required")
        sys.exit(1)
    
    logger.info(f"Python version: {sys.version}")
    
    # Install dependencies
    if install_requirements():
        logger.info("Installation completed successfully!")
        
        # Check environment
        logger.info("\nChecking environment configuration...")
        if check_environment():
            logger.info("All checks passed! You can now use MCP plugins.")
        else:
            logger.warning("Please configure your environment before using plugins.")
        
        show_usage()
    else:
        logger.error("Installation failed!")
        sys.exit(1)