import asyncio
from core import init_db

async def main():
    print("Iniciando migração de teste do SQLite...")
    await init_db()
    print("Migração concluída com sucesso.")

if __name__ == "__main__":
    asyncio.run(main())
