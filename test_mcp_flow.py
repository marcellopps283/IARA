import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
import httpx

async def try_mcp(url: str):
    print(f"Trying {url}")
    try:
        async with sse_client(url, httpx.AsyncClient(timeout=5.0)) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                print("TOOLS:", tools)
    except Exception as e:
        print("Error:", e)
        
if __name__ == "__main__":
    asyncio.run(try_mcp("http://localhost:3000/mcp"))

