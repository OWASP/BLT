import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import sys
import json

async def main():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "blt_mcp.server"]
    )
    
    print("Starting MCP server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Initialized. Fetching blt://v2/bugs...")
            
            try:
                result = await session.read_resource("blt://v2/bugs")
                text = result.contents[0].text
                print("\nRaw length:", len(text))
                data = json.loads(text)
                print("\nParsed JSON:")
                if isinstance(data, dict):
                    print("Keys:", data.keys())
                    if 'data' in data:
                        print(f"Items in data: {len(data['data'])}")
                elif isinstance(data, list):
                    print(f"Items in list: {len(data)}")
                else:
                    print("Type:", type(data))
                print("\nSuccess!")
            except Exception as e:
                print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
