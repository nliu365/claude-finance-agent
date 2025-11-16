#!/usr/bin/env python3
"""Test MCP server with ClaudeSDKClient"""

import asyncio
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    tool,
    create_sdk_mcp_server,
)

@tool("test_tool", "A simple test tool", {})
async def test_tool(args):
    return {
        "content": [{"type": "text", "text": "Tool executed successfully!"}]
    }

async def main():
    print("Testing MCP server with ClaudeSDKClient...")
    print("=" * 50)
    
    # Create MCP server
    server = create_sdk_mcp_server(
        name="test_server",
        version="1.0.0",
        tools=[test_tool]
    )
    
    options = ClaudeAgentOptions(
        mcp_servers={"test": server},
        allowed_tools=["mcp__test__test_tool"],
        max_turns=2,
    )
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query("Use the test_tool")
            
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(f"Response: {block.text}")
        
        print("\n✅ MCP server test successful!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
