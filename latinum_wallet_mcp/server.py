import asyncio
import requests

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio


def get_signed_transaction(targetWallet: str, amountLamports: int) -> dict:
    try:
        print("🔁 Calling /api/402wallet...")
        res = requests.post("http://localhost:3000/api/402wallet", json={
            "targetWallet": targetWallet,
            "amountLamports": amountLamports
        })

        res.raise_for_status()
        data = res.json()

        if not data.get("success") or not data.get("signedTransactionB64"):
            return {
                "success": False,
                "message": "❌ Failed to retrieve signed transaction from wallet."
            }

        return {
            "success": True,
            "signedTransactionB64": data["signedTransactionB64"],
            "message": f"✅ Signed transaction ready:\n{data['signedTransactionB64']}"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Error: {str(e)}"
        }

# Wrap it
get_signed_transaction = FunctionTool(get_signed_transaction)

# --- MCP App ---
app: Server = Server("mcp-latinum-wallet")

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [adk_to_mcp_tool_type(get_signed_transaction)]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    if name == get_signed_transaction.name:
        result = await get_signed_transaction.run_async(args=arguments, tool_context=None)
        return [mcp_types.TextContent(type="text", text=result.get("message", "❌ Failed."))]

    return [mcp_types.TextContent(type="text", text="❌ Unknown tool")]

async def run():
    async with mcp.server.stdio.stdio_server() as (r, w):
        await app.run(
            r, w,
            InitializationOptions(
                server_name=app.name,
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                ),
            )
        )

if __name__ == "__main__":
    asyncio.run(run())