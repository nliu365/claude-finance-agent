# Claude Finance Agent

An intelligent financial analysis system powered by Claude AI that autonomously analyzes SEC 10-K filings using specialized AI agents.

## Overview

Claude Finance Agent uses the Claude Agent SDK to deploy multiple specialized AI agents that work in parallel to analyze different sections of SEC 10-K filings. Each agent autonomously discovers and explores relevant sections, providing comprehensive financial analysis with multi-dimensional scoring and investment recommendations.

## AgentBeats Phase 1 Submission

Phase 1 artifacts are tracked in this repo, including:
- Dockerized Green Agent: `Dockerfile`
- Baseline Purple Agent: `purple_agent/server.py`
- Reproducibility: `docs/reproducibility.md`

## Finance Agent Benchmark Port (arXiv: 2508.00828)

This repo includes a minimal port of the Finance Agent benchmark under `benchmarks/finance_agent/`.
See `benchmarks/finance_agent/README.md` for setup, tool keys, and how to run the end-to-end harness.

## Features

- **Smart Section Discovery**: Agents autonomously identify and analyze relevant 10-K sections
- **Parallel Analysis**: Four specialized agents analyze different aspects simultaneously:
  - Business Agent (Item 1): Business model and competitive positioning
  - Risk Agent (Item 1A): Risk assessment and categorization
  - MD&A Agent (Item 7): Financial performance and management outlook
  - Financial Agent (Item 8): Balance sheet and financial statement analysis
- **Multi-Dimensional Scoring**: 17 metrics across 5 categories:
  - Business (25%): Model strength, competitive position, market opportunity
  - Financial (30%): Profitability, liquidity, debt management, cash flow quality
  - Growth (20%): Revenue growth, innovation, market expansion
  - Risk (15%): Operational, financial, market, and regulatory risks
  - Management (10%): Strategic clarity, execution capability, transparency
- **Investment Recommendations**: Automated ratings (Strong Buy, Buy, Hold, Underperform, Sell)
- **Batch Processing**: Analyze multiple 10-K filings in sequence
- **Structured Output**: JSON reports with detailed analyses and scores

## Architecture

The system uses a coordinator-agent architecture:

```
FinanceCoordinator
    |
    +-- Business Agent (explores Item 1)
    +-- Risk Agent (explores Item 1A)
    +-- MD&A Agent (explores Item 7)
    +-- Financial Agent (explores Item 8)
```

Each agent uses MCP (Model Context Protocol) tools to:
1. List available sections in the 10-K filing
2. Identify the correct section for their analysis domain
3. Read and analyze the section content
4. Return structured findings

## Prerequisites

- Python 3.11+
- Anthropic API key (Claude)
- Package manager: `uv` (recommended) or `pip`

## Installation

The project supports two installation methods: **uv** (modern, fast) and **pip/venv** (traditional).

### Option 1: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is an extremely fast Python package manager.

1. **Install uv** (if not already installed):
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv

# Or using Homebrew (macOS)
brew install uv
```

2. **Clone and setup**:
```bash
git clone <repository-url>
cd claude-finance-agent

# Run the uv setup script
chmod +x setup_uv.sh
./setup_uv.sh
```

3. **Configure your API key**:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

That's it! You can now use `uv run` to execute scripts without activating the virtual environment.

### Option 2: Using pip/venv (Traditional)

1. **Clone the repository**:
```bash
git clone <repository-url>
cd claude-finance-agent
```

2. **Set up the environment**:
```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

3. **Configure your API key**:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

**Alternative:** Use the provided setup script:
```bash
chmod +x setup_env.sh
./setup_env.sh
```

### API Key Configuration

You can also use a `.env` file instead of environment variables:

```bash
# Create .env file in project root
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

### Verify Installation

**Using uv:**
```bash
uv run python -c "import claude_agent_sdk; import anthropic; print('✅ Installation successful!')"
```

### Docker (Green Agent)

Build and run the Green Agent end-to-end with the sample 10-K data:

```bash
docker build -t claude-finance-agent .
docker run --rm -e ANTHROPIC_API_KEY=your-api-key-here claude-finance-agent
```

## Usage

### Quick Demo

Run a quick analysis on a sample 10-K filing:

```bash
chmod +x run_demo.sh
./run_demo.sh
```

### Single File Analysis

Analyze a specific 10-K filing:

**Using uv:**
```bash
uv run python scripts/finance_analyzer.py data/10k_2020_10_critical_sections/1137091_2020.json
```

**Using pip/venv:**
```bash
source .venv/bin/activate
python scripts/finance_analyzer.py data/10k_2020_10_critical_sections/1137091_2020.json
```

### Batch Analysis

Analyze all 10-K filings in a directory:

**Using uv:**
```bash
uv run python scripts/batch_analyzer.py
```

**Using pip/venv:**
```bash
source .venv/bin/activate
python scripts/batch_analyzer.py
```

With custom parameters:
```bash
# uv
uv run python scripts/batch_analyzer.py <data_dir> <output_dir> <limit>

# pip/venv
python scripts/batch_analyzer.py <data_dir> <output_dir> <limit>
```

Example:
```bash
uv run python scripts/batch_analyzer.py data/10k_2020_10_critical_sections data/results 5
```

### Baseline Purple Agent (A2A-Compatible)

Run the baseline Purple Agent HTTP server:

```bash
python purple_agent/server.py
```

Send predictions requests via the Green Agent runner:

```bash
python scripts/run_agent.py \
  --input evaluation/sample_labels.jsonl \
  --out evaluation/purple_outputs.jsonl \
  --use-purple \
  --purple-endpoint http://localhost:8000
```

## Project Structure

```
claude-finance-agent/
├── scripts/
│   ├── finance_analyzer.py    # Main single-file analyzer
│   └── batch_analyzer.py      # Batch processing script
├── data/
│   ├── 10k_2020_10_critical_sections/  # Sample 10-K data
│   └── results/                        # Analysis output (JSON)
├── tests/
│   ├── test_single_agent.py
│   ├── test_concurrent_vs_sequential.py
│   ├── test_sdk.py
│   ├── test_with_system_prompt.py
│   └── test_mcp.py
├── requirements.txt           # pip dependencies
├── pyproject.toml             # uv/modern Python project config
├── setup_env.sh               # Environment setup script (pip/venv)
├── setup_uv.sh                # Environment setup script (uv)
├── run_demo.sh                # Quick demo script
├── Dockerfile                 # Dockerized Green Agent
├── purple_agent/              # Baseline Purple Agent (A2A-compatible)
└── README.md                  # This file
```

## Input Data Format

The system expects 10-K filings in JSON format with the following structure:

```json
{
  "cik": "1137091",
  "year": "2020",
  "section_1": "Business section content...",
  "section_1A": "Risk factors content...",
  "section_7": "MD&A content...",
  "section_8": "Financial statements content..."
}
```

## Output Format

Analysis results are saved as JSON files with the following structure:

```json
{
  "timestamp": "2025-11-16T...",
  "file": "path/to/input.json",
  "section_analyses": {
    "business_agent": {
      "agent": "business_agent",
      "target": "Item 1 - Business",
      "section_key_found": "section_1",
      "analysis": "..."
    },
    ...
  },
  "scores": {
    "business_model_strength": 70.0,
    "competitive_position": 68.0,
    ...
    "overall_score": 68.5,
    "grade": "B- (Average)"
  },
  "recommendation": {
    "rating": "Hold",
    "confidence": "Medium",
    "overall_score": 68.5,
    "grade": "B- (Average)",
    "risk_level": "Moderate Risk",
    "investment_thesis": "Score: 68.5/100. Mixed signals."
  }
}
```

## Reproducibility

Two identical evaluations with the same configuration are recorded in:
- `docs/reproducibility.md`
- `evaluation/repro_run_1.jsonl`, `evaluation/repro_run_2.jsonl`
- `evaluation/repro_eval_1.json`, `evaluation/repro_eval_2.json`

## Scoring System

### Score Ranges
- **90-100**: A+ (Exceptional)
- **85-89**: A (Excellent)
- **80-84**: A- (Very Good)
- **75-79**: B+ (Good)
- **70-74**: B (Above Average)
- **65-69**: B- (Average)
- **60-64**: C+ (Below Average)
- **55-59**: C (Weak)
- **<55**: D (Poor)

### Recommendation Ratings
- **Strong Buy**: Score >= 80
- **Buy**: Score 70-79
- **Hold**: Score 60-69
- **Underperform**: Score 50-59
- **Sell**: Score < 50

## Development

### Running Tests

**Using uv:**
```bash
uv run pytest tests/
```

**Using pip/venv:**
```bash
source .venv/bin/activate
pytest tests/
```

### Code Formatting and Linting

**Using uv:**
```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Format code with black
uv run black scripts/ tests/

# Lint with ruff
uv run ruff check scripts/ tests/

# Type checking with mypy
uv run mypy scripts/
```

**Using pip/venv:**
```bash
# Install dev dependencies
pip install pytest pytest-asyncio black ruff mypy

# Format code
black scripts/ tests/

# Lint code
ruff check scripts/ tests/

# Type checking
mypy scripts/
```

### Adding Dependencies

**Using uv:**
```bash
# Add a new dependency
uv pip install package-name

# Update requirements.txt
uv pip freeze > requirements.txt

# Or edit pyproject.toml directly and run
uv pip install -e .
```

**Using pip/venv:**
```bash
pip install package-name
pip freeze > requirements.txt
```

### Adding Custom Agents

To add a new specialized agent, create a `SmartSectionAgent` instance in `create_four_smart_agents()`:

```python
custom_agent = SmartSectionAgent(
    agent_name="custom_agent",
    target_item="Item X - Section Name",
    system_prompt="Your agent's instructions..."
)
```

## Technical Details

- **Concurrency**: Agents run in parallel using `asyncio.gather()`
- **MCP Tools**: Custom tools for section discovery and reading
- **Max Turns**: Each agent has a limit of 4 turns to complete analysis
- **Content Limits**: Sections are truncated to 10,000 characters to manage context

## Known Limitations

- System prompts with MCP tools may cause 403 errors; instructions are embedded in queries instead
- Content truncation for large sections may limit analysis depth
- Scoring is currently heuristic-based and may benefit from more sophisticated ML models

## Acknowledgments

Built with the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk) by Anthropic.
