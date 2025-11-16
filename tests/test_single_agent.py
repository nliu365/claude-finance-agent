#!/usr/bin/env python3
"""Test a single agent to isolate the problem"""

import asyncio
import json
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    tool,
    create_sdk_mcp_server,
)

@tool("list_available_sections", "List all available sections", {"file_path": str})
async def list_available_sections(args):
    try:
        with open(args["file_path"], 'r') as f:
            data = json.load(f)
        
        sections = [k for k in sorted(data.keys()) if k.startswith('section_')]
        result_text = f"Found {len(sections)} sections: {', '.join(sections)}"
        
        return {"content": [{"type": "text", "text": result_text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

async def main():
    print("Testing single agent...")
    print("=" * 50)
    
    server = create_sdk_mcp_server(
        name="test_tools",
        version="1.0.0",
        tools=[list_available_sections]
    )
    
    options = ClaudeAgentOptions(
        mcp_servers={"test_tools": server},
        allowed_tools=["mcp__test_tools__list_available_sections"],
        max_turns=3,
    )
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            file_path = "data/10k_2020_10_critical_sections/1137091_2020.json"
            await client.query(f"Use list_available_sections to check sections in {file_path}")
            
            print("\nReceiving response...")
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(f"Text: {block.text}")
                        elif isinstance(block, ToolUseBlock):
                            print(f"Tool used: {block.name}")
                elif isinstance(msg, ResultMessage):
                    print(f"Result: {msg}")
        
        print("\n✅ Test completed!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
