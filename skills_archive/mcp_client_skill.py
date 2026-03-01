import os
import json
from transport import TransportClient

"""
Skill: mcp_client
Description: Bridge para servidores Model Context Protocol (MCP). Permite que a Kitty acesse ferramentas dinâmicas padronizadas abertas por servidores externos no Host ou Workers.
"""

def get_schema():
    return {
        "type": "function",
        "function": {
            "name": "call_mcp_tool",
            "description": "Call a tool exported by a local or remote Model Context Protocol (MCP) server.",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_command": {
                        "type": "string",
                        "description": "Command to start the MCP server (e.g., 'npx', 'python', 'mcp-server-sqlite')."
                    },
                    "server_args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Arguments for the server command (e.g., ['-y', '@modelcontextprotocol/server-sqlite', '--db', 'file.db'])."
                    },
                    "tool_name": {
                        "type": "string",
                        "description": "Name of the target tool exported by the MCP server."
                    },
                    "tool_args": {
                        "type": "object",
                        "description": "JSON object parameters to pass to the MCP tool."
                    }
                },
                "required": ["server_command", "server_args", "tool_name", "tool_args"]
            }
        }
    }

async def execute(kwargs):
    server_cmd = kwargs.get("server_command")
    server_args = kwargs.get("server_args", [])
    tool_name = kwargs.get("tool_name")
    tool_args = kwargs.get("tool_args", {})
    
    if not server_cmd or not tool_name:
        return "Erro: server_command e tool_name são obrigatórios."

    heavy_worker_ip = os.getenv("HEAVY_WORKER_IP", "127.0.0.1")
    target_port = 5556 # S21 FE
    
    payload = {
        "type": "call_mcp_tool",
        "server_command": server_cmd,
        "server_args": server_args,
        "tool_name": tool_name,
        "tool_args": tool_args
    }
    
    try:
        print(f"🔌 [MCP] Delegando execução da tool '{tool_name}' para o S21 FE...")
        client = TransportClient()
        response = await client.invoke_agent(heavy_worker_ip, target_port, payload, timeout=120)
        return f"Retorno do S21 FE (MCP):\n{json.dumps(response, indent=2)}"
    except Exception as e:
        return f"Falha na delegação MCP para S21 FE: {e}"
