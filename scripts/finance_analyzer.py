#!/usr/bin/env python3
"""
Finance Coordinator Agent - Direct Anthropic Version

Use Anthropic's default model settings for financial analysis.
Analyzes 4 core sections, letting agents explore and discover the actual key names of these sections.
"""

import asyncio
import json
import os
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    tool,
    create_sdk_mcp_server,
)


# ============================================================================
# Smart Tools
# ============================================================================

@tool("list_available_sections", "List all available sections in the 10-K JSON file", {
    "file_path": str
})
async def list_available_sections(args):
    """List all available sections and their basic information in the 10-K file."""
    try:
        with open(args["file_path"], 'r') as f:
            data = json.load(f)

        sections_info = []
        for key in sorted(data.keys()):
            if key.startswith('section_'):
                content = data[key]
                preview = content[:300].replace('\n', ' ')[:200]
                sections_info.append({
                    "key": key,
                    "length": len(content),
                    "preview": preview
                })

        result_text = f"""10-K Filing Information:
- CIK: {data.get('cik', 'N/A')}
- Year: {data.get('year', 'N/A')}
- Total Sections: {len(sections_info)}

Available Sections:
"""
        for info in sections_info:
            result_text += f"\n{info['key']} ({info['length']} chars):\n  Preview: {info['preview']}...\n"

        result_text += """
Common 10-K Section Mappings:
- Item 1 (Business): Usually section_1
- Item 1A (Risk Factors): Usually section_1A or section_1a
- Item 7 (MD&A): Usually section_7
- Item 8 (Financial Statements): Usually section_8

Use read_section to read the full content of any section."""

        return {
            "content": [{
                "type": "text",
                "text": result_text
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error: {str(e)}"
            }]
        }


@tool("read_section", "Read a specific section from the 10-K file", {
    "file_path": str,
    "section_key": str
})
async def read_section(args):
    """Read the full content of a specific section."""
    try:
        with open(args["file_path"], 'r') as f:
            data = json.load(f)

        section_key = args["section_key"]
        if section_key not in data:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: '{section_key}' not found. Use list_available_sections first."
                }]
            }

        content = data[section_key]

        # Limit length
        max_length = 10000
        if len(content) > max_length:
            truncated = content[:max_length]
            result_text = f"{truncated}\n\n[Content truncated. Showing first {max_length} of {len(content)} characters]"
        else:
            result_text = content

        return {
            "content": [{
                "type": "text",
                "text": result_text
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error: {str(e)}"
            }]
        }


# ============================================================================
# Scoring System
# ============================================================================

@dataclass
class CompanyScores:
    business_model_strength: float = 0.0
    competitive_position: float = 0.0
    market_opportunity: float = 0.0
    profitability: float = 0.0
    liquidity: float = 0.0
    debt_management: float = 0.0
    cash_flow_quality: float = 0.0
    revenue_growth: float = 0.0
    innovation_capability: float = 0.0
    market_expansion: float = 0.0
    operational_risk: float = 0.0
    financial_risk: float = 0.0
    market_risk: float = 0.0
    regulatory_risk: float = 0.0
    strategic_clarity: float = 0.0
    execution_capability: float = 0.0
    transparency: float = 0.0

    def overall_score(self) -> float:
        weights = {'business': 0.25, 'financial': 0.30, 'growth': 0.20, 'risk': 0.15, 'management': 0.10}
        business_avg = (self.business_model_strength + self.competitive_position + self.market_opportunity) / 3
        financial_avg = (self.profitability + self.liquidity + self.debt_management + self.cash_flow_quality) / 4
        growth_avg = (self.revenue_growth + self.innovation_capability + self.market_expansion) / 3
        risk_avg = (self.operational_risk + self.financial_risk + self.market_risk + self.regulatory_risk) / 4
        management_avg = (self.strategic_clarity + self.execution_capability + self.transparency) / 3
        return round(business_avg * weights['business'] + financial_avg * weights['financial'] +
                    growth_avg * weights['growth'] + risk_avg * weights['risk'] +
                    management_avg * weights['management'], 2)

    def get_grade(self) -> str:
        score = self.overall_score()
        if score >= 90: return "A+ (Exceptional)"
        elif score >= 85: return "A (Excellent)"
        elif score >= 80: return "A- (Very Good)"
        elif score >= 75: return "B+ (Good)"
        elif score >= 70: return "B (Above Average)"
        elif score >= 65: return "B- (Average)"
        elif score >= 60: return "C+ (Below Average)"
        elif score >= 55: return "C (Weak)"
        else: return "D (Poor)"

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['overall_score'] = self.overall_score()
        result['grade'] = self.get_grade()
        return result


# ============================================================================
# Smart Section Agent - Discovers section keys autonomously
# ============================================================================

class SmartSectionAgent:
    """Smart agent: knows what topic to analyze and finds the corresponding section itself."""

    def __init__(self, agent_name: str, target_item: str, system_prompt: str):
        self.agent_name = agent_name
        self.target_item = target_item  # e.g., "Item 1 - Business"
        self.system_prompt = system_prompt

        self.tools_server = create_sdk_mcp_server(
            name=f"{agent_name}_tools",
            version="1.0.0",
            tools=[list_available_sections, read_section]
        )

    async def analyze(self, file_path: str) -> Dict[str, Any]:
        """Analyze the section for the specified topic."""

        options = ClaudeAgentOptions(
            mcp_servers={f"{self.agent_name}_tools": self.tools_server},
            allowed_tools=[
                f"mcp__{self.agent_name}_tools__list_available_sections",
                f"mcp__{self.agent_name}_tools__read_section",
            ],
            # NOTE: system_prompt causes MCP tools to fail with 403 error
            # Using instructions in the query instead
            max_turns=4,
        )

        result = {
            "agent": self.agent_name,
            "target": self.target_item,
            "section_key_found": None,
            "analysis": "",
        }

        try:
            async with ClaudeSDKClient(options=options) as client:
                prompt = f"""You need to analyze {self.target_item} from a 10-K SEC filing.

File: {file_path}

Steps:
1. Use list_available_sections to see all available sections
2. Identify which section key corresponds to {self.target_item}
3. Use read_section with the correct section key to read the content
4. Provide your analysis

Provide analysis in this format:
## Summary
[Brief 2-3 sentence overview]

## Key Findings
- Finding 1
- Finding 2
- Finding 3

## Concerns/Risks
- Concern 1
- Concern 2

## Opportunities/Strengths
- Opportunity 1
- Opportunity 2

Start by exploring available sections."""

                await client.query(prompt)

                full_response = []
                section_key_used = None

                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                full_response.append(block.text)
                            elif isinstance(block, ToolUseBlock):
                                tool_name = block.name.split('__')[-1]
                                if tool_name == 'read_section':
                                    section_key_used = block.input.get('section_key')
                    elif isinstance(msg, ResultMessage):
                        print(f"  [{self.agent_name}] Completed")

                result["analysis"] = "\n".join(full_response)
                result["section_key_found"] = section_key_used

        except Exception as e:
            print(f"  [{self.agent_name}] Error: {e}")
            import traceback
            traceback.print_exc()
            result["analysis"] = f"Error: {str(e)}"

        return result


# ============================================================================
# Create 4 Specialized Smart Agents
# ============================================================================

def create_four_smart_agents() -> List[SmartSectionAgent]:
    """Create 4 smart agents, each responsible for one core section."""

    business_agent = SmartSectionAgent(
        agent_name="business_agent",
        target_item="Item 1 - Business",
        system_prompt="""You are a business strategy analyst.

Analyze the Business section (Item 1) which covers:
- Business overview and operations
- Products and services
- Markets and customers
- Competitive position
- Growth strategies

Provide insights on business model strength and competitive positioning."""
    )

    risk_agent = SmartSectionAgent(
        agent_name="risk_agent",
        target_item="Item 1A - Risk Factors",
        system_prompt="""You are a risk assessment specialist.

Analyze the Risk Factors section (Item 1A) which covers:
- Market risks
- Operational risks
- Financial risks
- Regulatory risks
- Strategic risks

Categorize and assess risk severity."""
    )

    mda_agent = SmartSectionAgent(
        agent_name="mda_agent",
        target_item="Item 7 - Management Discussion & Analysis",
        system_prompt="""You are a financial analyst specializing in MD&A.

Analyze the MD&A section (Item 7) which covers:
- Revenue trends
- Operating results
- Liquidity and capital resources
- Critical accounting policies
- Forward-looking statements

Focus on financial performance and management outlook."""
    )

    financial_agent = SmartSectionAgent(
        agent_name="financial_agent",
        target_item="Item 8 - Financial Statements",
        system_prompt="""You are a financial statements expert.

Analyze the Financial Statements section (Item 8) which covers:
- Balance sheet
- Income statement
- Cash flow statement
- Notes to financial statements

Identify financial strengths and weaknesses."""
    )

    return [business_agent, risk_agent, mda_agent, financial_agent]


# ============================================================================
# Finance Coordinator
# ============================================================================

class FinanceCoordinator:
    """Smart coordinator - uses smart agents to analyze 4 core sections."""

    def __init__(self):
        self.agents = create_four_smart_agents()

    async def analyze_company(self, file_path: str, output_dir: str = None) -> Dict[str, Any]:
        print("=" * 80)
        print("🏢 Finance Coordinator")
        print("   Using Claude Agent SDK with default settings")
        print("=" * 80)
        print(f"\n📄 File: {file_path}\n")
        print(f"🤖 Deploying {len(self.agents)} specialized agents...")
        print("   Each will explore and find its target section\n")

        print("📊 Phase 1: Parallel Section Discovery & Analysis")
        print("-" * 80)

        tasks = [agent.analyze(file_path) for agent in self.agents]
        results = await asyncio.gather(*tasks)

        print("\n✅ All analyses completed\n")

        # Display discovered sections
        print("🔍 Sections Discovered:")
        print("-" * 80)
        for r in results:
            key = r.get('section_key_found', 'N/A')
            print(f"  • {r['target']:45} → {key}")
        print()

        print("📈 Phase 2: Multi-Dimensional Scoring")
        print("-" * 80)

        scores = self._calculate_scores(results)

        print("\n💡 Phase 3: Investment Recommendation")
        print("-" * 80)

        recommendation = self._generate_recommendation(scores)

        # Get filename for results
        file_basename = os.path.basename(file_path).replace('.json', '')

        report = {
            "timestamp": datetime.now().isoformat(),
            "file": file_path,
            "section_analyses": {r['agent']: r for r in results},
            "scores": scores.to_dict(),
            "recommendation": recommendation,
        }

        # Save results
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{file_basename}_analysis.json")
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n💾 Results saved: {output_path}")

        return report

    def _calculate_scores(self, results: List[Dict[str, Any]]) -> CompanyScores:
        scores = CompanyScores()

        for r in results:
            agent = r['agent']
            text = r.get('analysis', '')

            if 'business' in agent:
                scores.business_model_strength = self._score(text, 70)
                scores.competitive_position = self._score(text, 68)
                scores.market_opportunity = self._score(text, 72)
            elif 'financial' in agent:
                scores.profitability = self._score(text, 65)
                scores.liquidity = self._score(text, 70)
                scores.debt_management = self._score(text, 68)
                scores.cash_flow_quality = self._score(text, 72)
            elif 'mda' in agent:
                scores.revenue_growth = self._score(text, 66)
                scores.innovation_capability = self._score(text, 64)
                scores.market_expansion = self._score(text, 68)
                scores.strategic_clarity = self._score(text, 75)
                scores.execution_capability = self._score(text, 70)
                scores.transparency = self._score(text, 78)
            elif 'risk' in agent:
                scores.operational_risk = 100 - self._score(text, 35)
                scores.financial_risk = 100 - self._score(text, 30)
                scores.market_risk = 100 - self._score(text, 40)
                scores.regulatory_risk = 100 - self._score(text, 32)

        return scores

    def _score(self, text: str, base: float) -> float:
        pos = sum(1 for w in ['strong', 'growth', 'opportunity', 'improve', 'solid'] if w in text.lower())
        neg = sum(1 for w in ['risk', 'decline', 'concern', 'challenge', 'weak'] if w in text.lower())
        return round(max(0, min(100, base + (pos - neg) * 2)), 2)

    def _generate_recommendation(self, scores: CompanyScores) -> Dict[str, Any]:
        overall = scores.overall_score()

        if overall >= 80: rating, conf = "Strong Buy", "High"
        elif overall >= 70: rating, conf = "Buy", "Medium-High"
        elif overall >= 60: rating, conf = "Hold", "Medium"
        elif overall >= 50: rating, conf = "Underperform", "Medium-Low"
        else: rating, conf = "Sell", "High"

        risk_avg = (scores.operational_risk + scores.financial_risk + scores.market_risk + scores.regulatory_risk) / 4
        risk_level = "Low" if risk_avg >= 75 else "Moderate" if risk_avg >= 60 else "Elevated" if risk_avg >= 45 else "High"

        return {
            "rating": rating,
            "confidence": conf,
            "overall_score": overall,
            "grade": scores.get_grade(),
            "risk_level": f"{risk_level} Risk",
            "investment_thesis": f"Score: {overall}/100. {'Strong fundamentals' if overall >= 70 else 'Mixed signals'}."
        }

    def print_report(self, report: Dict[str, Any]):
        print("\n" + "=" * 80)
        print("📋 ANALYSIS REPORT")
        print("=" * 80)

        s = report['scores']
        print(f"\n🎯 OVERALL SCORE: {s['overall_score']}/100")
        print(f"🏆 GRADE: {s['grade']}")

        r = report['recommendation']
        print(f"\n💡 RECOMMENDATION: {r['rating']} ({r['confidence']} confidence)")
        print(f"⚠️  RISK LEVEL: {r['risk_level']}")
        print(f"📝 {r['investment_thesis']}")
        print("=" * 80)


# ============================================================================
# Main
# ============================================================================

async def main():
    """Example: analyze a single file"""
    import sys

    # File path can be specified via command line arguments
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        # Default test file (relative to project root)
        test_file = "data/10k_2020_10_critical_sections/1137091_2020.json"

    # Results save directory (relative to project root)
    output_dir = "data/results"

    coordinator = FinanceCoordinator()
    report = await coordinator.analyze_company(test_file, output_dir=output_dir)
    coordinator.print_report(report)


if __name__ == "__main__":
    asyncio.run(main())
