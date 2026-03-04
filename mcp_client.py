"""
mcp_client.py — Model Context Protocol Client (Phase 17)

Este módulo atua como a fundação para a comunicação com Servidores MCP.
Ele gerencia o registro dos servidores no banco, descobre tools dinamicamente (list_tools)
e as executa (call_tool) com resiliência de timeout.
"""

import aiosqlite
import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional
import config

logger = logging.getLogger("mcp_client")
DEFAULT_TIMEOUT = 30.0

async def get_all_servers() -> List[Dict[str, Any]]:
    """Retorna todos os servidores MCP registrados na base."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mcp_servers") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def register_server(name: str, url: str, api_key: str = None) -> bool:
    """Registra ou atualiza um servidor MCP. Retorna True em sucesso."""
    try:
        async with aiosqlite.connect(str(config.DB_PATH)) as db:
            await db.execute("""
                INSERT INTO mcp_servers (name, url, api_key, status)
                VALUES (?, ?, ?, 'offline')
                ON CONFLICT(name) DO UPDATE SET url=excluded.url, api_key=excluded.api_key;
            """, (name, url, api_key))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Erro ao registrar servidor MCP {name}: {e}")
        return False

async def remove_server(name: str) -> bool:
    """Remove um servidor MCP registrado."""
    try:
        async with aiosqlite.connect(str(config.DB_PATH)) as db:
            await db.execute("DELETE FROM mcp_servers WHERE name=?", (name,))
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Erro ao remover servidor MCP {name}: {e}")
        return False

async def set_server_status(name: str, status: str):
    """Atualiza o status (online/offline) no banco."""
    try:
        async with aiosqlite.connect(str(config.DB_PATH)) as db:
            await db.execute("UPDATE mcp_servers SET status=? WHERE name=?", (status, name))
            await db.commit()
    except Exception as e:
        logger.debug(f"Erro silencioso gravando status {status} do servidor {name}: {e}")

async def _fetch_tools_from_server(server: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Consulta as tools disponíveis em um servidor MCP específico."""
    headers = {"Content-Type": "application/json"}
    if server.get("api_key"):
        headers["Authorization"] = f"Bearer {server['api_key']}"
    
    url = server["url"].rstrip("/")
    if not url.endswith("/tools"):
        url = f"{url}/tools"
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                await set_server_status(server["name"], "online")
                data = response.json()
                # Decorar cada tool com o nome do servidor, para roteamento futuro
                tools = data.get("tools", [])
                for t in tools:
                    # Inserir hint pra IARA saber de qual servidor a ferramenta vem
                    t["mcp_server"] = server["name"] 
                return tools
            else:
                logger.warning(f"Servidor MCP {server['name']} retornou status {response.status_code}")
                await set_server_status(server["name"], "offline")
                return []
    except Exception as e:
        logger.warning(f"Timeout/Falha ao listar tools no servidor MCP {server['name']}: {e}")
        await set_server_status(server["name"], "offline")
        return []

async def list_tools() -> List[Dict[str, Any]]:
    """Lista todas as ferramentas disponíveis em todos os servidores registrados (unificado)."""
    servers = await get_all_servers()
    all_tools = []
    
    # Processa paralelo para economizar tempo pingando os servidores
    tasks = [_fetch_tools_from_server(s) for s in servers]
    results = await asyncio.gather(*tasks)
    
    for r in results:
        all_tools.extend(r)
        
    return all_tools

async def call_tool(server_name: str, tool_name: str, arguments: Dict[str, Any] = None, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Invoca uma ferramenta remota num servidor MCP. Tratamento de timeouts (anti-trava) incluso."""
    if arguments is None:
        arguments = {}
        
    servers = await get_all_servers()
    target = next((s for s in servers if s["name"] == server_name), None)
    
    if not target:
        return f"Erro: Servidor MCP '{server_name}' não encontrado/registrado."
        
    headers = {"Content-Type": "application/json"}
    if target.get("api_key"):
        headers["Authorization"] = f"Bearer {target['api_key']}"
        
    url = target["url"].rstrip("/")
    if not url.endswith("/call"):
        url = f"{url}/call"
        
    payload = {
        "tool": tool_name,
        "arguments": arguments
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("result", str(data))
            else:
                return f"Erro na Ferramenta Remota ({response.status_code}): {response.text[:200]}"
                
    except httpx.TimeoutException:
        logger.error(f"Timeout (>{timeout}s) ao chamar tool '{tool_name}' no MCP '{server_name}'")
        return f"Ferramenta {tool_name} (MCP {server_name}) indisponível no momento (Timeout após {timeout}s). Aja adequadamente."
    except Exception as e:
        logger.error(f"Erro fatal chamando tool '{tool_name}' no MCP '{server_name}': {e}")
        return f"Falha na comunicação com servidor MCP {server_name}: {e}"

async def get_status_report() -> str:
    """Gera um diagnóstico completo dos servidores (comando /mcp status)."""
    servers = await get_all_servers()
    if not servers:
        return "Nenhum servidor MCP registrado. Use `/mcp add <nome> <url>` para adicionar."
        
    # Pinga todos os servidores chamando list_tools pra saber quem está online
    all_tools = await list_tools()
    total_tools = len(all_tools)
    
    # Busca os servidores reatualizados com o status modificado após o list_tools
    updated_servers = await get_all_servers()
    
    lines = ["🔌 **Status MCP (Model Context Protocol)**\n"]
    for s in updated_servers:
        status_icon = "🟢" if s["status"] == "online" else "🔴"
        lines.append(f"- {status_icon} **{s['name']}** (`{s['url']}`)")
        
    lines.append(f"\n🛠️ **Total de ferramentas plugadas:** {total_tools}")
    
    return "\n".join(lines)
