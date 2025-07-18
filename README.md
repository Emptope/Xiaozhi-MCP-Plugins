# Xiaozhi-MCP-Plugins

Xiaozhi-MCP-Plugins 是为 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 项目开发的 MCP (Model Context Protocol) 插件集合。

## Quick Start

1. **设置环境变量**

   ```bash
   set MCP_ENDPOINT=ws://your-websocket-server:port
   ```

2. **安装依赖**

   ```bash
   python install.py
   ```

3. **启动所有插件**

   ```bash
   python mcp_manager.py --all
   ```

4. **查看运行状态**

   ```bash
   python mcp_manager.py --status
   ```

## mcp_manager 功能概述

### 核心功能

1. **插件自动发现**
   - 扫描项目目录中的所有插件
   - 识别包含 `FastMCP` 或 `mcp.tool` 的 Python 文件
   - 自动生成插件配置

2. **生命周期管理**
   - 启动/停止单个或多个插件
   - 监控插件运行状态
   - 处理异常退出和自动清理

3. **依赖管理**
   - 自动安装 `requirements.txt` 中的依赖
   - 确保插件运行环境完整

### 使用方法

```bash
# 启动所有插件
python mcp_manager.py --all

# 启动所有插件，但排除指定插件
python mcp_manager.py --exclude Calculator-common_calculate

# 启动指定插件
python mcp_manager.py --plugin Calculator-common_calculate

# 启动指定文件夹中的插件
python mcp_manager.py --folder Calculator

# 列出所有可用插件
python mcp_manager.py --list

# 查看插件状态
python mcp_manager.py --status

# 停止指定插件
python mcp_manager.py --stop Calculator-common_calculate

# 停止所有插件
python mcp_manager.py --stop-all

# 显示帮助信息
python mcp_manager.py --help
```

## 环境配置

### 必需环境变量

```bash
# Windows
set MCP_ENDPOINT=<your_websocket_endpoint>

# Linux/Mac
export MCP_ENDPOINT=<your_websocket_endpoint>
```

### 安装依赖

```bash
pip install -r requirements.txt
```

或使用项目提供的安装脚本：

```bash
python install.py
```

## 插件开发

### 插件结构

每个插件应该：

- 位于独立的目录中
- 包含至少一个使用 FastMCP 的 Python 文件
- 实现标准的 MCP 协议

### 示例插件

```python
from mcp.server.fastmcp import FastMCP
import sys
from loguru import logger

# 创建 MCP 服务器
mcp = FastMCP("YourPlugin")

@mcp.tool()
def your_function(param: str) -> dict:
    """工具描述"""
    try:
        # 你的逻辑
        result = "处理结果"
        logger.info(f"执行成功: {result}")
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"执行失败: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    logger.info("插件启动中...")
    mcp.run(transport="stdio")
```

## 故障排除

### 常见问题

1. **插件无法启动**
   - 检查 `MCP_ENDPOINT` 环境变量是否设置
   - 确认依赖是否正确安装
   - 查看日志输出中的错误信息

2. **连接失败**
   - 验证 WebSocket 服务器是否运行
   - 检查网络连接和防火墙设置
   - 确认端点 URL 格式正确

3. **插件意外退出**
   - 查看插件的错误日志
   - 检查插件代码中的异常处理
   - 使用 `--status` 命令查看详细状态

## 许可证

本项目采用 GPL-3.0 许可证，详见 [LICENSE](LICENSE) 文件。
