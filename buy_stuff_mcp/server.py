import asyncio

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# --- Import tool functions ---
from services.product_finder import find_products
from services.product_buyer import buy_products
from core.utils import url_to_base64_image

# --- Wrap as ADK tools ---
find_tool = FunctionTool(find_products)
buy_tool = FunctionTool(buy_products)

# --- MCP App ---
app: Server = Server("mcp-latinum")

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [
        adk_to_mcp_tool_type(find_tool),
        adk_to_mcp_tool_type(buy_tool),
    ]

SELLER_WALLET = "TODO: put me somewhere safe"

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.TextContent | mcp_types.ImageContent]:
    if name == find_tool.name:
        result = await find_tool.run_async(args=arguments, tool_context=None)
        if result.get("status") != "success":
            return [mcp_types.TextContent(type="text", text=result.get("message", "❌ Failed to find products"))]

        contents: list[mcp_types.TextContent | mcp_types.ImageContent] = []
        for product in result["products"]:
            b64_data, mime_type = url_to_base64_image(product["image"])
            contents.append(mcp_types.TextContent(
                type="text",
                text=f"🛒 {product['name']}\n💰 Price: €{product['price']:.2f}\nUUID: {product['product_id']}\nWallet: {SELLER_WALLET}\nLamports: {product['price']*100}"
            ))
            contents.append(mcp_types.ImageContent(
                type="image",
                mimeType=mime_type,
                data=b64_data
            ))
        return contents

    elif name == buy_tool.name:
        result = await buy_tool.run_async(args=arguments, tool_context=None)
        return [mcp_types.TextContent(type="text", text=result.get("message", "Something went wrong."))]

    return [mcp_types.TextContent(type="text", text="Tool not found")]

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
