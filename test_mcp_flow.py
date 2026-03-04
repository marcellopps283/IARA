import asyncio
import mcp_client
from core import init_db

async def run_mcp_test():
    print("Iniciando DB...")
    await init_db()
    
    # 1. Checando status vazio
    print("\n--- Status Inicial ---")
    status = await mcp_client.get_status_report()
    print(status)
    
    # 2. Adicionando um servidor fake
    print("\n--- Adicionando Servidor Fake ---")
    await mcp_client.register_server("fake_browser_mcp", "http://localhost:3000/mcp")
    
    # 3. Listando
    servers = await mcp_client.get_all_servers()
    print("Servidores no banco:", servers)
    
    # 4. Checando status agora (vai tentar fazer o list_tools que deve falhar pois localhost:3000 nao existe, 
    # testando a resiliência a errors).
    print("\n--- Status Com Servidor Registrado (Offline Esperado) ---")
    status = await mcp_client.get_status_report()
    print(status)
    
    # 5. Removendo
    print("\n--- Removendo Servidor ---")
    await mcp_client.remove_server("fake_browser_mcp")
    servers = await mcp_client.get_all_servers()
    print("Servidores no banco apos remocao:", servers)
    
if __name__ == "__main__":
    asyncio.run(run_mcp_test())
