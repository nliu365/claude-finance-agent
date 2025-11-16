#!/usr/bin/env python3
"""
Test concurrent execution vs sequential execution
Verify if concurrency causes 403 errors
"""

import asyncio
import json
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    tool,
    create_sdk_mcp_server,
)


@tool("list_sections", "List sections", {"file_path": str})
async def list_sections(args):
    try:
        with open(args["file_path"], 'r') as f:
            data = json.load(f)
        sections = [k for k in sorted(data.keys()) if k.startswith('section_')]
        return {"content": [{"type": "text", "text": f"Found: {', '.join(sections[:5])}..."}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {e}"}]}


async def run_agent(agent_id: int, file_path: str):
    """Run a single agent"""
    print(f"[Agent {agent_id}] Starting...")
    
    server = create_sdk_mcp_server(
        name=f"agent_{agent_id}_tools",
        version="1.0.0",
        tools=[list_sections]
    )
    
    options = ClaudeAgentOptions(
        mcp_servers={f"agent_{agent_id}": server},
        allowed_tools=[f"mcp__agent_{agent_id}__list_sections"],
        max_turns=2,
    )
    
    result = {"agent_id": agent_id, "success": False, "response": ""}
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(f"Use list_sections to check {file_path}")
            
            responses = []
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            responses.append(block.text)
            
            result["response"] = " ".join(responses)
            result["success"] = "API Error" not in result["response"] and "403" not in result["response"]
            
            status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
            print(f"[Agent {agent_id}] {status}")
            
    except Exception as e:
        result["response"] = f"Exception: {str(e)}"
        print(f"[Agent {agent_id}] ❌ Exception: {e}")
    
    return result


async def test_sequential():
    """Sequential execution test"""
    print("\n" + "=" * 60)
    print("Test 1: Sequential execution of 4 agents")
    print("=" * 60)
    
    file_path = "data/10k_2020_10_critical_sections/1137091_2020.json"
    results = []
    
    for i in range(1, 5):
        result = await run_agent(i, file_path)
        results.append(result)
        await asyncio.sleep(0.5)  # Wait 0.5 seconds between agents

    success_count = sum(1 for r in results if r["success"])
    print(f"\nResults: {success_count}/4 agents succeeded")
    return results


async def test_concurrent():
    """Concurrent execution test"""
    print("\n" + "=" * 60)
    print("Test 2: Concurrent execution of 4 agents")
    print("=" * 60)
    
    file_path = "data/10k_2020_10_critical_sections/1137091_2020.json"
    
    tasks = [run_agent(i, file_path) for i in range(1, 5)]
    results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r["success"])
    print(f"\nResults: {success_count}/4 agents succeeded")
    return results


async def main():
    print("=" * 60)
    print("Concurrent vs Sequential Execution Comparison Test")
    print("=" * 60)

    # Test 1: Sequential execution
    sequential_results = await test_sequential()

    # Wait a bit
    await asyncio.sleep(2)

    # Test 2: Concurrent execution
    concurrent_results = await test_concurrent()

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    seq_success = sum(1 for r in sequential_results if r["success"])
    con_success = sum(1 for r in concurrent_results if r["success"])

    print(f"Sequential execution: {seq_success}/4 succeeded")
    print(f"Concurrent execution: {con_success}/4 succeeded")

    if seq_success > con_success:
        print("\n✅ Hypothesis confirmed: concurrent execution does cause issues!")
        print("   Recommend modifying finance_analyzer.py to use sequential execution")
    elif seq_success == con_success == 4:
        print("\n✅ Both methods succeeded, the problem may be elsewhere")
    else:
        print("\n⚠️  Both methods have issues, further investigation needed")

    # Display failed responses
    print("\nFailed agent response examples:")
    for r in concurrent_results:
        if not r["success"]:
            print(f"  Agent {r['agent_id']}: {r['response'][:100]}...")
            break


if __name__ == "__main__":
    asyncio.run(main())
