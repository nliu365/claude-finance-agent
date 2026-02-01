#!/usr/bin/env python3
"""测试 system_prompt 是否导致问题"""

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


async def run_with_prompt(use_system_prompt: bool):
    """Helper function to test with/without system_prompt. Not a pytest test."""
    print(f"\n{'='*60}")
    print(f"测试: {'WITH' if use_system_prompt else 'WITHOUT'} system_prompt")
    print('='*60)
    
    tools_server = create_sdk_mcp_server(
        name="test_tools",
        version="1.0.0",
        tools=[list_available_sections]
    )
    
    options_dict = {
        "mcp_servers": {"test_tools": tools_server},
        "allowed_tools": ["mcp__test_tools__list_available_sections"],
        "max_turns": 2,
    }
    
    if use_system_prompt:
        # 使用和 finance_analyzer.py 一样的 system_prompt
        options_dict["system_prompt"] = """You are a business strategy analyst.

Analyze the Business section (Item 1) which covers:
- Business overview and operations
- Products and services

Provide insights on business model strength."""
    
    options = ClaudeAgentOptions(**options_dict)
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            file_path = "data/10k_2020_10_critical_sections/1137091_2020.json"
            await client.query(f"Use list_available_sections to check {file_path}")
            
            tool_called = False
            got_403 = False
            
            async for msg in client.receive_response():
                if hasattr(msg, 'data') and isinstance(msg.data, dict) and 'tools' in msg.data:
                    tools_list = msg.data.get('tools', [])
                    print(f"SystemMessage tools: {tools_list[:6]}")
                
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            if "403" in block.text or "API Error" in block.text:
                                got_403 = True
                                print(f"❌ Got 403 error!")
                        elif isinstance(block, ToolUseBlock):
                            tool_called = True
                            print(f"✅ Tool called: {block.name}")
            
            if tool_called:
                print("✅ SUCCESS - Tool was called")
            elif got_403:
                print("❌ FAILED - Got 403 error, tools not available")
            else:
                print("⚠️  UNCLEAR - No tool call, no 403")
                
    except Exception as e:
        print(f"❌ Exception: {e}")


async def main():
    print("="*60)
    print("对比测试：system_prompt 的影响")
    print("="*60)
    
    await run_with_prompt(use_system_prompt=False)
    await asyncio.sleep(1)
    await run_with_prompt(use_system_prompt=True)


if __name__ == "__main__":
    asyncio.run(main())
