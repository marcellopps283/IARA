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
import time
from typing import List, Dict, Any, Optional
import config

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

logger = logging.getLogger("mcp_client")
DEFAULT_TIMEOUT = 30.0

_tools_cache = {
    "tools": [],
    "expires_at": 0
}
DEFAULT_TIMEOUT = 30.0

async def get_all_servers() -> List[Dict[str, Any]]:
    """Retorna todos os servidores MCP registrados na base."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mcp_servers") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_server_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Retorna um servidor MCP específico da base (otimizado semânticamente)."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mcp_servers WHERE name=? LIMIT 1", (name,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

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
    """Consulta as tools disponíveis em um servidor MCP específico usando o SDK oficial."""
    headers = {}
    if server.get("api_key"):
        headers["Authorization"] = f"Bearer {server['api_key']}"
    
    # Supondo SSE por padrão. Em servidores Stdio, precisaríamos de outro branch.
    url = server["url"]
        
    try:
        # Tenta usar o SDK MCP nativo para recuperar tools
        async with sse_client(url, httpx.AsyncClient(timeout=5.0, headers=headers)) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                response = await session.list_tools()
                
                await set_server_status(server["name"], "online")
                tools_list = []
                
                # A resposta de list_tools() no SDK possui o atributo .tools
                for raw_t in response.tools:
                    # Converte o schema nativo do objeto Tool para dict
                    # Tool model has name, description, inputSchema
                    t = {
                        "name": raw_t.name,
                        "description": raw_t.description,
                        "inputSchema": getattr(raw_t, "inputSchema", {"type": "object", "properties": {}}),
                        "mcp_server": server["name"]
                    }
                    tools_list.append(t)
                return tools_list

    except Exception as e:
        logger.warning(f"Timeout/Falha ao listar tools no servidor MCP {server['name']} ({url}): {e}")
        await set_server_status(server["name"], "offline")
        return []

async def list_tools() -> List[Dict[str, Any]]:
    """Lista todas as ferramentas disponíveis em todos os servidores registrados (unificado). Com cache de 60s."""
    global _tools_cache
    
    now = time.time()
    if now < _tools_cache["expires_at"]:
        return _tools_cache["tools"]
        
    servers = await get_all_servers()
    all_tools = []
    
    # Processa paralelo para economizar tempo pingando os servidores
    tasks = [_fetch_tools_from_server(s) for s in servers]
    results = await asyncio.gather(*tasks)
    
    for r in results:
        all_tools.extend(r)
        
    # Salva no cache com TTL de 60s
    _tools_cache["tools"] = all_tools
    _tools_cache["expires_at"] = now + 60
        
    return all_tools

async def call_tool(server_name: str, tool_name: str, arguments: Dict[str, Any] = None, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Invoca uma ferramenta remota num servidor MCP. Usa ClientSession e tem tratamento de timeouts (anti-trava) incluso."""
    if arguments is None:
        arguments = {}
        
    target = await get_server_by_name(server_name)
    
    if not target:
        return f"Erro: Servidor MCP '{server_name}' não encontrado/registrado."
        
    headers = {}
    if target.get("api_key"):
        headers["Authorization"] = f"Bearer {target['api_key']}"
        
    url = target["url"]
    
    try:
        # Aplicamos o timeout configurável no AsyncClient usado pelo sse_client
        async with sse_client(url, httpx.AsyncClient(timeout=timeout, headers=headers)) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                response = await session.call_tool(tool_name, arguments)
                
                # O CallToolResult do MCP tem .content e .isError
                if response.isError:
                    return f"Erro na Ferramenta Remota: {response.content}"
                    
                # Extrai o texto da resposta
                outputs = []
                for content in response.content:
                    # Pode ser TextContent ou ImageContent.
                    if getattr(content, "text", None):
                        outputs.append(content.text)
                    elif getattr(content, "data", None):
                        outputs.append(f"[Media/Image Content: {content.mimeType}]")
                        
                return "\n".join(outputs) if outputs else "Tool executada sem retorno."
                
    except TimeoutError:
        logger.error(f"Timeout nativo (>{timeout}s) ao chamar tool '{tool_name}' no MCP '{server_name}'")
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
