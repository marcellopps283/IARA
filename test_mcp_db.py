import asyncio
from core import init_db
import aiosqlite
import config

async def test_mcp_table():
    await init_db()
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mcp_servers'") as cursor:
            res = await cursor.fetchone()
            if res:
                print("Tabela mcp_servers criada com sucesso!")
            else:
                print("Falha ao criar tabela mcp_servers.")

if __name__ == "__main__":
    asyncio.run(test_mcp_table())
