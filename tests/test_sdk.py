#!/usr/bin/env python3
"""Simple test to verify Claude Agent SDK works"""

import asyncio
from claude_agent_sdk import query, AssistantMessage, TextBlock

async def main():
    print("Testing Claude Agent SDK...")
    print("=" * 50)
    
    try:
        async for message in query(prompt="What is 2 + 2?"):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Response: {block.text}")
        print("\n✅ SDK is working correctly!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
