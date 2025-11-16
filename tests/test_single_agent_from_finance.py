#!/usr/bin/env python3
"""
测试从 finance_analyzer.py 中提取的单个agent
看看是否能重现问题
"""

import asyncio
import json
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
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
        return {"content": [{"type": "text", "text": f"Found: {', '.join(sections[:5])}..."}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {e}"}]}


async def main():
    print("Testing single agent from finance_analyzer pattern...")
    print("=" * 60)
    
    # 使用和 finance_analyzer.py 完全相同的模式
    tools_server = create_sdk_mcp_server(
        name="test_agent_tools",
        version="1.0.0",
        tools=[list_available_sections]
    )
    
    options = ClaudeAgentOptions(
        mcp_servers={"test_agent_tools": tools_server},
        allowed_tools=["mcp__test_agent_tools__list_available_sections"],
        max_turns=2,
    )
    
    print(f"MCP servers: {list(options.mcp_servers.keys())}")
    print(f"Allowed tools: {options.allowed_tools}")
    print()
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            file_path = "data/10k_2020_10_critical_sections/1137091_2020.json"
            await client.query(f"Use list_available_sections to check {file_path}")
            
            async for msg in client.receive_response():
                print(f"Message type: {type(msg).__name__}")
                if hasattr(msg, 'data') and isinstance(msg.data, dict) and 'tools' in msg.data:
                    tools_list = msg.data.get('tools', [])
                    print(f"Available tools in SystemMessage: {tools_list[:5]}")
                
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(f"Text: {block.text[:150]}")
                            if "403" in block.text or "API Error" in block.text:
                                print("❌ GOT 403 ERROR - MCP tools not loaded!")
                            else:
                                print("✅ Response looks normal")
                        elif isinstance(block, ToolUseBlock):
                            print(f"✅ Tool used: {block.name}")
        
        print("\n✅ Test completed")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
