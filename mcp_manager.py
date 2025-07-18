#!/usr/bin/env python3
"""
MCP Plugin Manager

Script for managing and launching MCP plugins, supports starting all plugins or specific plugins.

Usage:
    python mcp_manager.py --all                           # Start all plugins
    python mcp_manager.py --exclude plugin1 plugin2       # Start all plugins except plugin1 and plugin2
    python mcp_manager.py --plugin plugin1                # Start specific plugin
    python mcp_manager.py --folder Calculator             # Start all plugins in Calculator folder
    python mcp_manager.py --list                          # List all available plugins
    python mcp_manager.py --status                        # Show plugin status
    python mcp_manager.py --stop plugin1                  # Stop specific plugin
    python mcp_manager.py --stop-all                      # Stop all plugins
    python mcp_manager.py --help                          # Show help information
"""

import os
import sys
import subprocess
import argparse
import signal
import time
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure loguru logger
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | Manager | {message}", level="INFO")

class MCPManager:
    """MCP Plugin Manager"""
    
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path.cwd()
        self.plugin_configs = {}
        self.processes = {}
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Discover plugins
        self._discover_plugins()
    
    def _discover_plugins(self) -> None:
        """Discover all MCP plugins in workspace"""
        plugins = {}
        
        # Scan all directories in workspace
        for item in self.workspace_dir.iterdir():
            if not item.is_dir() or item.name.startswith('.'):
                continue
                
            # Scan all .py files in the directory for MCP indicators
            for py_file in item.glob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'FastMCP' not in content and 'mcp.tool' not in content:
                            continue
                    
                    # Generate plugin name: always use format "folder-filename"
                    folder_name = item.name.replace('mcp-', '') if item.name.startswith('mcp-') else item.name
                    plugin_name = f"{folder_name}-{py_file.stem}"
                    
                    plugins[plugin_name] = {
                        'dir': str(item),
                        'main_file': str(py_file),
                        'pipe_script': self._find_pipe_script(),
                        'requirements': str(self.workspace_dir / 'requirements.txt') if (self.workspace_dir / 'requirements.txt').exists() else None
                    }
                    
                except Exception as e:
                    logger.warning(f"Error reading {py_file}: {e}")
        
        self.plugin_configs = plugins
        logger.info(f"Found {len(plugins)} plugins: {', '.join(plugins.keys())}")

    def list_plugins(self) -> None:
        """List all available plugins with detailed information"""
        logger.info("=== Available Plugins ===")
        if not self.plugin_configs:
            logger.info("No plugins found")
            return
        
        # Group plugins by directory for better display
        plugins_by_dir = {}
        for name, config in self.plugin_configs.items():
            dir_name = Path(config['dir']).name
            if dir_name not in plugins_by_dir:
                plugins_by_dir[dir_name] = []
            plugins_by_dir[dir_name].append((name, config))
        
        for dir_name, plugins in plugins_by_dir.items():
            logger.info(f"\n{dir_name}/")
            for plugin_name, config in plugins:
                main_file = Path(config['main_file']).name
                logger.info(f"  {plugin_name}: {main_file}")
        
        logger.info(f"\nTotal: {len(self.plugin_configs)} plugins available")
    
    def _find_pipe_script(self) -> Optional[str]:
        """Find pipe script in root directory"""
        root_pipe = self.workspace_dir / 'mcp_pipe.py'
        if root_pipe.exists():
            return str(root_pipe)
        return None
    
    def install_dependencies(self) -> bool:
        """Install dependencies from root requirements.txt"""
        requirements_file = self.workspace_dir / 'requirements.txt'
        
        if not requirements_file.exists():
            return True
        
        try:
            logger.info("Installing dependencies...")
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
            ], capture_output=True, text=True, cwd=str(self.workspace_dir))
            
            if result.returncode == 0:
                logger.info("Dependencies installed")
                return True
            else:
                logger.error(f"Failed to install dependencies: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error installing dependencies: {e}")
            return False
    
    def start_plugin(self, plugin_name: str) -> bool:
        """Start specified plugin"""
        if plugin_name not in self.plugin_configs:
            logger.error(f"Plugin {plugin_name} not found")
            return False
        
        if plugin_name in self.processes:
            logger.warning(f"Plugin {plugin_name} already running")
            return True
        
        config = self.plugin_configs[plugin_name]
        
        # Check MCP_ENDPOINT environment variable
        endpoint = os.getenv('MCP_ENDPOINT')
        if not endpoint:
            logger.error("Please set MCP_ENDPOINT environment variable")
            return False
        
        # Install dependencies
        if not self.install_dependencies():
            return False
        
        try:
            # Check if pipe script exists
            pipe_script = config.get('pipe_script')
            if not pipe_script:
                logger.error(f"Plugin {plugin_name} missing pipe script")
                return False
            
            # Start plugin process with output directly to terminal
            cmd = [sys.executable, pipe_script, config['dir'], os.path.basename(config['main_file'])]
            logger.info(f"Starting {plugin_name}...")
            
            # Don't capture stdout/stderr, let them go directly to terminal
            process = subprocess.Popen(
                cmd,
                text=True,
                env=os.environ.copy()  # Ensure environment variables are passed
            )
            
            self.processes[plugin_name] = process
            logger.info(f"{plugin_name} started (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Error starting {plugin_name}: {e}")
            return False
    
    def stop_plugin(self, plugin_name: str) -> bool:
        """Stop specified plugin"""
        if plugin_name not in self.processes:
            logger.warning(f"Plugin {plugin_name} not running")
            return True
        
        try:
            process = self.processes[plugin_name]
            process.terminate()
            
            # Wait for process to end
            try:
                process.wait(timeout=5)
                logger.info(f"{plugin_name} stopped")
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {plugin_name}")
                process.kill()
                process.wait()
            
            del self.processes[plugin_name]
            return True
            
        except Exception as e:
            logger.error(f"Error stopping {plugin_name}: {e}")
            return False
    
    def start_all_plugins(self, exclude_plugins: List[str] = None) -> None:
        """Start all available plugins except excluded ones"""
        if not self.plugin_configs:
            logger.warning("No plugins to start")
            return
        
        exclude_plugins = exclude_plugins or []
        available_plugins = [name for name in self.plugin_configs.keys() if name not in exclude_plugins]
        
        if not available_plugins:
            logger.warning("No plugins to start after exclusions")
            return
        
        if exclude_plugins:
            logger.info(f"Excluding plugins: {', '.join(exclude_plugins)}")
        
        logger.info(f"Starting {len(available_plugins)} plugins...")
        
        success_count = 0
        for plugin_name in available_plugins:
            if self.start_plugin(plugin_name):
                success_count += 1
                time.sleep(1)  # Brief delay between starts
        
        logger.info(f"Started {success_count}/{len(available_plugins)} plugins")
        
        # Keep the manager running to show plugin output
        if success_count > 0:
            logger.info("Press Ctrl+C to stop all plugins")
            try:
                # Wait for interrupt signal
                while True:
                    time.sleep(1)
                    # Check if any processes have died
                    dead_processes = []
                    for name, process in self.processes.items():
                        if process.poll() is not None:
                            dead_processes.append(name)
                    
                    # Clean up dead processes
                    for name in dead_processes:
                        logger.warning(f"{name} stopped unexpectedly")
                        del self.processes[name]
                    
                    # If all processes are dead, exit
                    if not self.processes:
                        logger.info("All plugins stopped")
                        break
                        
            except KeyboardInterrupt:
                pass  # Will be handled by signal handler
    
    def start_folder_plugins(self, folder_name: str) -> None:
        """Start all plugins in specified folder"""
        if not self.plugin_configs:
            logger.warning("No plugins to start")
            return
        
        # Find plugins in the specified folder
        folder_plugins = [name for name, config in self.plugin_configs.items() 
                         if Path(config['dir']).name == folder_name]
        
        if not folder_plugins:
            logger.warning(f"No plugins found in folder '{folder_name}'")
            return
        
        logger.info(f"Starting {len(folder_plugins)} plugins from folder '{folder_name}'...")
        
        success_count = 0
        for plugin_name in folder_plugins:
            if self.start_plugin(plugin_name):
                success_count += 1
                time.sleep(1)  # Brief delay between starts
        
        logger.info(f"Started {success_count}/{len(folder_plugins)} plugins from '{folder_name}'")
        
        # Keep the manager running to show plugin output
        if success_count > 0:
            logger.info("Press Ctrl+C to stop all plugins")
            try:
                # Wait for interrupt signal
                while True:
                    time.sleep(1)
                    # Check if any processes have died
                    dead_processes = []
                    for name, process in self.processes.items():
                        if process.poll() is not None:
                            dead_processes.append(name)
                    
                    # Clean up dead processes
                    for name in dead_processes:
                        logger.warning(f"{name} stopped unexpectedly")
                        del self.processes[name]
                    
                    # If all processes are dead, exit
                    if not self.processes:
                        logger.info("All plugins stopped")
                        break
                        
            except KeyboardInterrupt:
                pass  # Will be handled by signal handler
    
    def stop_all_plugins(self) -> None:
        """Stop all running plugins"""
        if not self.processes:
            logger.info("No plugins running")
            return
        
        logger.info(f"Stopping {len(self.processes)} plugins...")
        
        # Create a copy of the keys to avoid modification during iteration
        plugin_names = list(self.processes.keys())
        for plugin_name in plugin_names:
            self.stop_plugin(plugin_name)
    
    def get_plugin_status(self) -> Dict[str, str]:
        """Get status of all plugins"""
        status = {}
        
        for plugin_name in self.plugin_configs:
            if plugin_name in self.processes:
                process = self.processes[plugin_name]
                if process.poll() is None:
                    status[plugin_name] = f"Running (PID: {process.pid})"
                else:
                    status[plugin_name] = f"Stopped (Exit: {process.returncode})"
                    # Clean up stopped process
                    del self.processes[plugin_name]
            else:
                status[plugin_name] = "Not running"
        
        return status
    
    def show_status(self) -> None:
        """Display status of all plugins"""
        status = self.get_plugin_status()
        
        logger.info("=== Plugin Status ===")
        for plugin_name, plugin_status in status.items():
            logger.info(f"{plugin_name}: {plugin_status}")
    
    def _signal_handler(self, sig, frame):
        """Handle interrupt signals"""
        logger.info("Stopping all plugins...")
        self.stop_all_plugins()
        sys.exit(0)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='MCP Plugin Manager')
    group = parser.add_mutually_exclusive_group(required=False)
    
    group.add_argument('--all', action='store_true', help='Start all plugins')
    group.add_argument('--plugin', type=str, help='Start specific plugin')
    group.add_argument('--folder', type=str, help='Start all plugins in specific folder')
    group.add_argument('--list', action='store_true', help='List all available plugins')
    group.add_argument('--status', action='store_true', help='Show plugin status')
    group.add_argument('--stop', type=str, help='Stop specific plugin')
    group.add_argument('--stop-all', action='store_true', help='Stop all plugins')
    group.add_argument('--exclude', type=str, nargs='+', help='Exclude specific plugins when starting all (space-separated list)')
    
    args = parser.parse_args()
    
    # If no main action is specified but exclude is provided, default to starting all with exclusions
    if not any([args.all, args.plugin, args.folder, args.list, args.status, args.stop, args.stop_all]) and args.exclude:
        args.all = True
    
    # Ensure at least one action is specified
    if not any([args.all, args.plugin, args.folder, args.list, args.status, args.stop, args.stop_all]):
        parser.error("At least one action must be specified")
    
    # Create manager instance
    manager = MCPManager()
    
    try:
        if args.all:
            exclude_list = args.exclude if args.exclude else []
            # Validate excluded plugins exist
            if exclude_list:
                invalid_plugins = [p for p in exclude_list if p not in manager.plugin_configs]
                if invalid_plugins:
                    logger.warning(f"Unknown plugins in exclude list: {', '.join(invalid_plugins)}")
                    exclude_list = [p for p in exclude_list if p in manager.plugin_configs]
            
            manager.start_all_plugins(exclude_list)
        elif args.folder:
            manager.start_folder_plugins(args.folder)
        elif args.plugin:
            if manager.start_plugin(args.plugin):
                logger.info(f"{args.plugin} running. Press Ctrl+C to stop.")
                try:
                    while True:
                        time.sleep(1)
                        # Check if process is still alive
                        if args.plugin in manager.processes:
                            process = manager.processes[args.plugin]
                            if process.poll() is not None:
                                logger.warning(f"{args.plugin} stopped unexpectedly")
                                break
                        else:
                            break
                except KeyboardInterrupt:
                    pass  # Will be handled by signal handler
        elif args.list:
            manager.list_plugins()
        elif args.status:
            manager.show_status()
        elif args.stop:
            manager.stop_plugin(args.stop)
        elif args.stop_all:
            manager.stop_all_plugins()
            
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()