"""
Agent Output Passing - Complete Guide
======================================

Shows exactly how one agent's output becomes another agent's input
in the flexible orchestrator system.

Output Passing Mechanisms:
1. File-based communication (primary method)
2. Task tool with context injection
3. Orchestrator-mediated passing
4. Shared workspace coordination
"""

import asyncio
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions
from flexible_orchestrator import AgentRegistry, AgentConfig, FlexibleOrchestrator


# ============================================================================
# PATTERN 1: File-Based Output Passing (Most Common)
# ============================================================================

async def example_file_based_passing():
    """
    Most common pattern: Agents write files, next agents read them.
    The orchestrator coordinates by telling agents which files to read.
    """
    print("\n" + "="*70)
    print("PATTERN 1: FILE-BASED OUTPUT PASSING")
    print("="*70 + "\n")
    
    registry = AgentRegistry()
    workspace = Path("./file_passing_workspace")
    workspace.mkdir(exist_ok=True)
    
    # Register agents
    registry.register(AgentConfig(
        name="researcher",
        description="Researches topics and saves to markdown",
        tools=["WebSearch", "WebFetch", "Write"],
        capabilities=["research"],
        system_prompt="Research topics and save findings to markdown files."
    ))
    
    registry.register(AgentConfig(
        name="analyzer",
        description="Analyzes research files",
        tools=["Read", "Write", "Bash"],
        capabilities=["analysis"],
        system_prompt="Read research files and create analysis reports."
    ))
    
    registry.register(AgentConfig(
        name="summarizer",
        description="Creates summaries from analysis",
        tools=["Read", "Write"],
        capabilities=["summarization"],
        system_prompt="Read analysis files and create executive summaries."
    ))
    
    # Create orchestrator with explicit output passing instructions
    orchestrator = FlexibleOrchestrator(registry, str(workspace))
    
    task = """
    Research AI trends, analyze the findings, and create an executive summary.
    
    OUTPUT PASSING STRUCTURE:
    
    Step 1: researcher agent
      - Research AI trends in 2025
      - OUTPUT FILE: ai_research.md
      - This file will be used by the analyzer
    
    Step 2: analyzer agent
      - Read ai_research.md from Step 1
      - Analyze the research findings
      - OUTPUT FILE: analysis_report.md
      - This file will be used by the summarizer
    
    Step 3: summarizer agent
      - Read analysis_report.md from Step 2
      - Create executive summary
      - OUTPUT FILE: executive_summary.md
    
    IMPORTANT: Each agent must specify which file from the previous step to read.
    Use the Task tool to spawn agents with explicit file references.
    """
    
    await orchestrator.execute(task=task, permission_mode="plan")
    
    # Show the output passing chain
    print("\n" + "="*70)
    print("OUTPUT PASSING CHAIN:")
    print("="*70)
    
    if (workspace / "ai_research.md").exists():
        print("\n✓ Step 1 Output: ai_research.md")
        print(f"  Size: {(workspace / 'ai_research.md').stat().st_size} bytes")
    
    if (workspace / "analysis_report.md").exists():
        print("\n✓ Step 2 Output: analysis_report.md")
        print(f"  Input: ai_research.md")
        print(f"  Size: {(workspace / 'analysis_report.md').stat().st_size} bytes")
    
    if (workspace / "executive_summary.md").exists():
        print("\n✓ Step 3 Output: executive_summary.md")
        print(f"  Input: analysis_report.md")
        print(f"  Size: {(workspace / 'executive_summary.md').stat().st_size} bytes")


# ============================================================================
# PATTERN 2: Explicit Task Tool with Context Injection
# ============================================================================

async def example_explicit_context_injection():
    """
    Show how the orchestrator explicitly passes context between agents
    using the Task tool's prompt parameter.
    """
    print("\n" + "="*70)
    print("PATTERN 2: EXPLICIT CONTEXT INJECTION VIA TASK TOOL")
    print("="*70 + "\n")
    
    workspace = Path("./context_injection_workspace")
    workspace.mkdir(exist_ok=True)
    
    # Manual orchestration showing explicit context passing
    print("Step 1: Agent A gathers data\n")
    
    agent_a_options = ClaudeAgentOptions(
        cwd=str(workspace),
        allowed_tools=["WebSearch", "Write"],
        permission_mode="acceptEdits",
        system_prompt="You gather data and save to files."
    )
    
    agent_a_task = """
    Search for the top 3 programming languages in 2025.
    Save your findings to: languages.json
    
    Format:
    {
        "languages": [
            {"name": "Python", "rank": 1, "usage": "..."},
            ...
        ]
    }
    """
    
    async for msg in query(prompt=agent_a_task, options=agent_a_options):
        pass
    
    print("✓ Agent A complete: languages.json created\n")
    
    # Read Agent A's output to pass to Agent B
    languages_file = workspace / "languages.json"
    if languages_file.exists():
        languages_data = languages_file.read_text()
        
        print("Step 2: Agent B analyzes Agent A's output\n")
        
        agent_b_options = ClaudeAgentOptions(
            cwd=str(workspace),
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
            system_prompt="You analyze data and create reports."
        )
        
        # Inject Agent A's output into Agent B's prompt
        agent_b_task = f"""
        You are receiving output from the previous agent.
        
        PREVIOUS AGENT OUTPUT (from languages.json):
        {languages_data}
        
        YOUR TASK:
        1. Analyze this data
        2. Compare the languages
        3. Create a comparison report
        4. Save to: comparison_report.md
        """
        
        async for msg in query(prompt=agent_b_task, options=agent_b_options):
            pass
        
        print("✓ Agent B complete: comparison_report.md created")
        print("  Input: languages.json data (injected into prompt)")


# ============================================================================
# PATTERN 3: Orchestrator-Mediated Passing with State Management
# ============================================================================

class StatefulOrchestrator(FlexibleOrchestrator):
    """
    Enhanced orchestrator that tracks outputs and explicitly passes them
    """
    
    def __init__(self, agent_registry, workspace_dir="./workspace"):
        super().__init__(agent_registry, workspace_dir)
        self.agent_outputs = {}  # Track outputs from each agent
    
    def _create_orchestrator_prompt_with_passing(self, task: str) -> str:
        """
        Create prompt that explicitly handles output passing
        """
        agent_context = self.registry.to_prompt_context()
        
        return f"""You are a LEAD ORCHESTRATOR with explicit output passing.

{agent_context}

YOUR TASK:
{task}

OUTPUT PASSING PROTOCOL:

When spawning agents with the Task tool, you MUST:

1. For the FIRST agent:
   Task({{
       "subagent_type": "agent-name",
       "prompt": "Do X and save to OUTPUT_FILE.ext",
       "expected_output": "OUTPUT_FILE.ext"
   }})

2. For SUBSEQUENT agents (that need previous outputs):
   Task({{
       "subagent_type": "agent-name",
       "prompt": "Read INPUT_FILE.ext from previous agent, process it, save to OUTPUT_FILE.ext",
       "inputs": ["INPUT_FILE.ext"],  # Files this agent needs
       "expected_output": "OUTPUT_FILE.ext"
   }})

3. EXPLICIT FILE REFERENCES:
   Always tell agents the exact filename to read from previous steps.
   Example: "Read research_data.json created by researcher agent..."

4. EXECUTION ORDER:
   Ensure agents run in the correct order based on dependencies.
   Use run_in_background: false when order matters.

CREATE A CLEAR CHAIN:
Agent A → output_a.ext → Agent B → output_b.ext → Agent C → final_output.ext

Show your decomposition plan with explicit input/output files for each step.
"""
    
    async def execute_with_tracking(self, task: str):
        """Execute and track all outputs"""
        prompt = self._create_orchestrator_prompt_with_passing(task)
        
        options = ClaudeAgentOptions(
            cwd=str(self.workspace),
            allowed_tools=["Read", "Write", "Task", "WebSearch"],
            permission_mode="plan",
            system_prompt="You coordinate agents with explicit output passing."
        )
        
        print("\nExecuting with output tracking...\n")
        
        async for message in query(prompt=prompt, options=options):
            print(message)
        
        # Track all created files
        print("\n" + "="*70)
        print("OUTPUT PASSING CHAIN:")
        print("="*70)
        
        files = sorted(self.workspace.glob("*.*"), key=lambda x: x.stat().st_mtime)
        
        for i, file_path in enumerate(files, 1):
            print(f"\nStep {i}: {file_path.name}")
            print(f"  Size: {file_path.stat().st_size} bytes")
            
            # Show first 100 chars to verify content
            content = file_path.read_text()[:100]
            print(f"  Preview: {content}...")


async def example_stateful_orchestration():
    """
    Use the stateful orchestrator that explicitly tracks output passing
    """
    print("\n" + "="*70)
    print("PATTERN 3: ORCHESTRATOR-MEDIATED OUTPUT PASSING")
    print("="*70 + "\n")
    
    registry = AgentRegistry()
    
    # Register agents
    registry.register(AgentConfig(
        name="data-collector",
        description="Collects data from various sources",
        tools=["WebSearch", "Write"],
        capabilities=["data-collection"],
        system_prompt="Collect data and save to structured files."
    ))
    
    registry.register(AgentConfig(
        name="data-processor",
        description="Processes and transforms data",
        tools=["Read", "Write", "Bash"],
        capabilities=["data-processing"],
        system_prompt="Read data files, process them, and save results."
    ))
    
    registry.register(AgentConfig(
        name="report-generator",
        description="Generates reports from processed data",
        tools=["Read", "Write"],
        capabilities=["reporting"],
        system_prompt="Read processed data and create formatted reports."
    ))
    
    orchestrator = StatefulOrchestrator(registry, "./stateful_workspace")
    
    task = """
    Create a pipeline to analyze web framework popularity:
    
    1. data-collector: Collect data about web frameworks → save to frameworks_data.json
    2. data-processor: Read frameworks_data.json → process and rank → save to rankings.json
    3. report-generator: Read rankings.json → create final report → save to report.md
    
    Show explicit input/output for each step.
    """
    
    await orchestrator.execute_with_tracking(task)


# ============================================================================
# PATTERN 4: Parallel Agents with Consolidation
# ============================================================================

async def example_parallel_with_consolidation():
    """
    Multiple agents run in parallel, then one agent consolidates all outputs
    """
    print("\n" + "="*70)
    print("PATTERN 4: PARALLEL OUTPUTS → CONSOLIDATION")
    print("="*70 + "\n")
    
    registry = AgentRegistry()
    workspace = Path("./parallel_consolidation_workspace")
    workspace.mkdir(exist_ok=True)
    
    # Register parallel workers
    for i in range(3):
        registry.register(AgentConfig(
            name=f"researcher-{i+1}",
            description=f"Researches specific topic {i+1}",
            tools=["WebSearch", "Write"],
            capabilities=["research"],
            system_prompt=f"Research your assigned topic and save findings."
        ))
    
    # Register consolidator
    registry.register(AgentConfig(
        name="consolidator",
        description="Consolidates multiple research outputs",
        tools=["Read", "Write"],
        capabilities=["consolidation"],
        system_prompt="Read all research files and create unified report."
    ))
    
    orchestrator = FlexibleOrchestrator(registry, str(workspace))
    
    task = """
    Research three different aspects of cloud computing in parallel:
    
    PARALLEL EXECUTION (run_in_background: true):
    
    1. researcher-1 agent:
       - Research AWS services
       - OUTPUT: aws_research.md
    
    2. researcher-2 agent:
       - Research Azure services
       - OUTPUT: azure_research.md
    
    3. researcher-3 agent:
       - Research GCP services
       - OUTPUT: gcp_research.md
    
    CONSOLIDATION (after all parallel agents complete):
    
    4. consolidator agent:
       - INPUTS: aws_research.md, azure_research.md, gcp_research.md
       - Read all three files
       - Create comprehensive comparison
       - OUTPUT: cloud_comparison.md
    
    IMPORTANT: Consolidator must wait for all researchers to finish.
    Explicitly tell consolidator to read all three input files.
    """
    
    await orchestrator.execute(task=task, permission_mode="plan")
    
    # Show the parallel → consolidation pattern
    print("\n" + "="*70)
    print("PARALLEL OUTPUT CONSOLIDATION:")
    print("="*70)
    
    research_files = list(workspace.glob("*_research.md"))
    print(f"\nParallel Outputs: {len(research_files)} files")
    for f in research_files:
        print(f"  • {f.name}")
    
    if (workspace / "cloud_comparison.md").exists():
        print(f"\nConsolidated Output: cloud_comparison.md")
        print(f"  Inputs: {', '.join(f.name for f in research_files)}")


# ============================================================================
# PATTERN 5: Data Structure Passing (JSON/Structured Data)
# ============================================================================

async def example_structured_data_passing():
    """
    Agents pass structured data (JSON) instead of unstructured text
    """
    print("\n" + "="*70)
    print("PATTERN 5: STRUCTURED DATA PASSING")
    print("="*70 + "\n")
    
    registry = AgentRegistry()
    workspace = Path("./structured_data_workspace")
    workspace.mkdir(exist_ok=True)
    
    registry.register(AgentConfig(
        name="api-fetcher",
        description="Fetches data and returns as JSON",
        tools=["WebSearch", "Write"],
        capabilities=["data-fetching"],
        system_prompt="Fetch data and save as structured JSON."
    ))
    
    registry.register(AgentConfig(
        name="json-transformer",
        description="Transforms JSON data structures",
        tools=["Read", "Write", "Bash"],
        capabilities=["data-transformation"],
        system_prompt="Read JSON, transform it, output new JSON."
    ))
    
    registry.register(AgentConfig(
        name="json-reporter",
        description="Creates reports from JSON data",
        tools=["Read", "Write"],
        capabilities=["reporting"],
        system_prompt="Read JSON data and create human-readable reports."
    ))
    
    orchestrator = FlexibleOrchestrator(registry, str(workspace))
    
    task = """
    Create a data pipeline with structured JSON passing:
    
    Step 1: api-fetcher
      - Fetch data about top tech companies
      - OUTPUT: companies.json
      - Format: {{"companies": [{{"name": "...", "revenue": "...", ...}}]}}
    
    Step 2: json-transformer
      - INPUT: companies.json
      - Transform: Calculate market share percentages
      - Add field: "market_share_percent" to each company
      - OUTPUT: companies_enriched.json
    
    Step 3: json-reporter
      - INPUT: companies_enriched.json
      - Read the JSON data
      - Create markdown report with tables
      - OUTPUT: companies_report.md
    
    USE STRUCTURED DATA:
    - Always use JSON for data passing between agents
    - Validate JSON structure at each step
    - Include schema/format in prompts
    """
    
    await orchestrator.execute(task=task, permission_mode="plan")
    
    print("\n" + "="*70)
    print("STRUCTURED DATA CHAIN:")
    print("="*70)
    
    import json
    
    if (workspace / "companies.json").exists():
        print("\n✓ Step 1: companies.json (raw data)")
        data = json.loads((workspace / "companies.json").read_text())
        print(f"  Records: {len(data.get('companies', []))}")
    
    if (workspace / "companies_enriched.json").exists():
        print("\n✓ Step 2: companies_enriched.json (transformed)")
        data = json.loads((workspace / "companies_enriched.json").read_text())
        print(f"  Records: {len(data.get('companies', []))}")
        print(f"  New fields added by transformer")
    
    if (workspace / "companies_report.md").exists():
        print("\n✓ Step 3: companies_report.md (final report)")
        print(f"  Generated from enriched JSON")


# ============================================================================
# HELPER: Visualize Output Passing
# ============================================================================

def visualize_output_chain(workspace: Path):
    """
    Visualize the output passing chain by analyzing file timestamps
    """
    files = sorted(workspace.glob("*.*"), key=lambda x: x.stat().st_mtime)
    
    if not files:
        print("No output files found")
        return
    
    print("\n" + "="*70)
    print("OUTPUT PASSING VISUALIZATION")
    print("="*70 + "\n")
    
    for i, file_path in enumerate(files):
        prefix = "└→" if i == len(files) - 1 else "├→"
        print(f"{prefix} {file_path.name}")
        print(f"   Size: {file_path.stat().st_size} bytes")
        
        # Try to detect what agent created it (from content)
        content = file_path.read_text()[:200]
        if "research" in content.lower():
            print(f"   Likely from: researcher agent")
        elif "analysis" in content.lower():
            print(f"   Likely from: analyzer agent")
        elif "summary" in content.lower():
            print(f"   Likely from: summarizer agent")
        
        if i < len(files) - 1:
            print(f"   ↓")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """
    Demonstrate all output passing patterns
    """
    
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║  Agent Output Passing - Complete Examples                       ║
    ║  How one agent's output becomes another agent's input            ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    examples = {
        "1": ("File-Based Passing", example_file_based_passing),
        "2": ("Context Injection via Task", example_explicit_context_injection),
        "3": ("Orchestrator-Mediated Passing", example_stateful_orchestration),
        "4": ("Parallel → Consolidation", example_parallel_with_consolidation),
        "5": ("Structured Data (JSON)", example_structured_data_passing)
    }
    
    print("\nOutput Passing Patterns:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    choice = input("\nSelect pattern (1-5) or 'all': ").strip()
    
    if choice == "all":
        for name, func in examples.values():
            print(f"\n\n{'#'*70}")
            print(f"# {name}")
            print(f"{'#'*70}\n")
            await func()
    elif choice in examples:
        name, func = examples[choice]
        await func()
    else:
        print("Running pattern 1 by default...")
        await example_file_based_passing()


if __name__ == "__main__":
    asyncio.run(main())
