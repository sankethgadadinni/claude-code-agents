"""
Multi-Agent Orchestration System with Claude Agent SDK
=======================================================

This example demonstrates:
1. Task decomposition and planning
2. Coordinating multiple specialized agents
3. Passing outputs between agents
4. Tracking agent activity with hooks
5. Synthesizing results from multiple agents

Architecture:
- Lead Agent: Plans and coordinates the overall workflow
- Specialized Agents: Execute specific subtasks (researcher, analyst, writer)
- Hooks: Track all agent activities and tool calls
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import dataclass, field

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)


@dataclass
class AgentActivity:
    """Track individual agent activities"""
    agent_name: str
    tool_name: str
    timestamp: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any] = field(default_factory=dict)
    parent_tool_id: str = None


class ActivityTracker:
    """Tracks all agent activities using SDK hooks"""
    
    def __init__(self):
        self.activities: List[AgentActivity] = []
        self.subagent_map: Dict[str, str] = {}  # tool_use_id -> agent_name
        
    def pre_tool_use_hook(
        self, 
        input_data: Dict[str, Any], 
        tool_use_id: str | None,
        context: Any
    ) -> Dict[str, Any]:
        """Called before each tool execution"""
        tool_name = input_data.get("tool_name", "Unknown")
        
        # Detect subagent spawning
        if tool_name == "Task":
            subagent_type = input_data.get("tool_input", {}).get("subagent_type", "")
            agent_name = f"{subagent_type.upper()}-{len(self.subagent_map) + 1}"
            if tool_use_id:
                self.subagent_map[tool_use_id] = agent_name
        
        # Determine which agent made this call
        parent_id = input_data.get("parent_tool_use_id")
        agent_name = self.subagent_map.get(parent_id, "LEAD-AGENT")
        
        activity = AgentActivity(
            agent_name=agent_name,
            tool_name=tool_name,
            timestamp=datetime.now().isoformat(),
            input_data=input_data,
            parent_tool_id=parent_id
        )
        self.activities.append(activity)
        
        return {}  # No modification to tool execution
    
    def post_tool_use_hook(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        tool_use_id: str | None,
        context: Any
    ) -> Dict[str, Any]:
        """Called after each tool execution"""
        # Update the last activity with output
        if self.activities:
            self.activities[-1].output_data = output_data
        
        return {}
    
    def print_summary(self):
        """Print a human-readable activity summary"""
        print("\n" + "="*70)
        print("AGENT ACTIVITY SUMMARY")
        print("="*70)
        
        # Group by agent
        agent_groups = {}
        for activity in self.activities:
            if activity.agent_name not in agent_groups:
                agent_groups[activity.agent_name] = []
            agent_groups[activity.agent_name].append(activity)
        
        for agent_name, activities in agent_groups.items():
            print(f"\n[{agent_name}] - {len(activities)} tool calls")
            for activity in activities:
                print(f"  → {activity.tool_name}")
                if "query" in str(activity.input_data).lower():
                    query = activity.input_data.get("tool_input", {}).get("query", "")
                    if query:
                        print(f"    Query: {query[:80]}...")
        
        print("\n" + "="*70)


class MultiAgentOrchestrator:
    """
    Orchestrates multiple specialized agents to complete complex tasks
    """
    
    def __init__(self, workspace_dir: str = "./workspace"):
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(exist_ok=True)
        self.tracker = ActivityTracker()
        
    def _create_lead_agent_prompt(self, task: str) -> str:
        """
        Create a comprehensive prompt for the lead agent that includes
        task decomposition and coordination instructions
        """
        return f"""You are the LEAD AGENT coordinating a team of specialized subagents to complete complex tasks.

YOUR CURRENT TASK:
{task}

YOUR WORKFLOW:
1. PLAN: Break down the task into logical subtasks
2. ASSIGN: Spawn specialized subagents for each subtask
3. COORDINATE: Monitor subagent progress and collect their outputs
4. SYNTHESIZE: Combine all results into a final deliverable

AVAILABLE SUBAGENT TYPES:
- research-specialist: For web research and information gathering
- data-analyst: For data analysis, processing, and visualization
- technical-writer: For creating documentation and reports

STEP-BY-STEP PROCESS:
1. First, create a plan by listing all subtasks needed
2. For each subtask, spawn an appropriate subagent using the Task tool:
   - Provide clear, specific instructions
   - Specify expected outputs (files, data, summaries)
   - Set run_in_background: true for parallel execution
3. Collect outputs from each subagent
4. Synthesize all findings into a comprehensive final result
5. Save the final result to {self.workspace}/final_report.md

Begin by creating your execution plan."""

    def _create_subagent_config(
        self, 
        subagent_type: str, 
        prompt: str,
        allowed_tools: List[str] = None
    ) -> Dict[str, Any]:
        """Configure a specialized subagent"""
        
        tool_configs = {
            "research-specialist": {
                "tools": ["Read", "Write", "WebSearch", "WebFetch"],
                "system_prompt": """You are a specialized RESEARCH AGENT.
Your job is to thoroughly research the given topic and create a detailed research note.

YOUR PROCESS:
1. Search the web for relevant information
2. Fetch and analyze key sources
3. Extract important findings
4. Write a comprehensive markdown summary
5. Save your findings to a file

Be thorough and cite your sources."""
            },
            "data-analyst": {
                "tools": ["Read", "Write", "Bash"],
                "system_prompt": """You are a specialized DATA ANALYSIS AGENT.
Your job is to analyze data, create visualizations, and generate insights.

YOUR PROCESS:
1. Read and understand the data
2. Perform statistical analysis
3. Create visualizations (using matplotlib/seaborn if needed)
4. Generate a summary of key insights
5. Save your analysis to files

Focus on actionable insights."""
            },
            "technical-writer": {
                "tools": ["Read", "Write"],
                "system_prompt": """You are a specialized TECHNICAL WRITING AGENT.
Your job is to create clear, well-structured documentation.

YOUR PROCESS:
1. Read all input materials
2. Organize information logically
3. Write clear, concise content
4. Use proper markdown formatting
5. Save your document to a file

Write for clarity and accessibility."""
            }
        }
        
        config = tool_configs.get(subagent_type, {
            "tools": ["Read", "Write"],
            "system_prompt": f"You are a specialized {subagent_type} agent."
        })
        
        return {
            "subagent_type": subagent_type,
            "prompt": prompt,
            "allowed_tools": allowed_tools or config["tools"],
            "system_prompt": config["system_prompt"]
        }
    
    async def execute_task(self, task: str) -> Dict[str, Any]:
        """
        Execute a complex task using multi-agent orchestration
        
        Args:
            task: High-level task description
            
        Returns:
            Dict containing execution results and metadata
        """
        print(f"\n{'='*70}")
        print(f"STARTING MULTI-AGENT ORCHESTRATION")
        print(f"{'='*70}")
        print(f"Task: {task}\n")
        
        # Create hooks for activity tracking
        from claude_agent_sdk import Hooks
        hooks = Hooks(
            pre_tool_use=[self.tracker.pre_tool_use_hook],
            post_tool_use=[self.tracker.post_tool_use_hook]
        )
        
        # Configure the lead agent with plan mode
        # Use "plan" mode to see the orchestration plan before execution
        options = ClaudeAgentOptions(
            cwd=str(self.workspace),
            allowed_tools=["Read", "Write", "Task", "Bash"],
            permission_mode="plan",  # Creates plan first, then executes after approval
            hooks=hooks,
            system_prompt="You are the lead orchestrator agent coordinating specialized subagents."
        )
        
        # Execute with the lead agent
        lead_prompt = self._create_lead_agent_prompt(task)
        
        result = {
            "task": task,
            "status": "running",
            "outputs": [],
            "final_report": None
        }
        
        print("Lead agent is planning and executing...\n")
        
        async for message in query(prompt=lead_prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        # Print agent reasoning
                        if len(block.text) > 100:
                            print(f"[LEAD] {block.text[:100]}...")
                        else:
                            print(f"[LEAD] {block.text}")
                    
                    elif isinstance(block, ToolUseBlock):
                        # Log tool usage
                        print(f"[TOOL] {block.name}")
        
        # Check for final report
        final_report_path = self.workspace / "final_report.md"
        if final_report_path.exists():
            result["final_report"] = final_report_path.read_text()
            result["status"] = "completed"
        else:
            result["status"] = "completed_no_report"
        
        # Collect all output files
        for file_path in self.workspace.glob("**/*"):
            if file_path.is_file():
                result["outputs"].append(str(file_path))
        
        # Print activity summary
        self.tracker.print_summary()
        
        print(f"\n{'='*70}")
        print(f"ORCHESTRATION COMPLETE")
        print(f"{'='*70}")
        print(f"Status: {result['status']}")
        print(f"Output files: {len(result['outputs'])}")
        
        return result


# ============================================================================
# EXAMPLE 1: Simple Multi-Agent Research Task
# ============================================================================

async def example_research_task():
    """
    Example: Research a topic using multiple specialized agents
    """
    orchestrator = MultiAgentOrchestrator(workspace_dir="./research_workspace")
    
    task = """
    Research the current state of quantum computing in 2025.
    
    Requirements:
    1. Search for recent developments and breakthroughs
    2. Identify key companies and research institutions
    3. Analyze practical applications and use cases
    4. Create a comprehensive report with your findings
    
    Spawn at least 2 research agents to work in parallel on different aspects.
    """
    
    result = await orchestrator.execute_task(task)
    return result


# ============================================================================
# EXAMPLE 2: Complex Multi-Stage Pipeline
# ============================================================================

class PipelineOrchestrator(MultiAgentOrchestrator):
    """
    Enhanced orchestrator for multi-stage pipelines where outputs
    from one agent explicitly feed into the next
    """
    
    async def execute_pipeline(self, stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a multi-stage pipeline where each stage can use outputs from previous stages
        
        Args:
            stages: List of stage definitions with agent_type, task, and dependencies
        """
        print(f"\n{'='*70}")
        print(f"STARTING PIPELINE ORCHESTRATION")
        print(f"{'='*70}")
        print(f"Stages: {len(stages)}\n")
        
        stage_outputs = {}
        
        for i, stage in enumerate(stages):
            stage_name = stage.get("name", f"Stage-{i+1}")
            agent_type = stage["agent_type"]
            task = stage["task"]
            dependencies = stage.get("dependencies", [])
            
            print(f"\n--- Stage {i+1}: {stage_name} ---")
            print(f"Agent: {agent_type}")
            
            # Inject dependency outputs into task prompt
            if dependencies:
                dep_context = "\n\nPREVIOUS STAGE OUTPUTS:\n"
                for dep in dependencies:
                    if dep in stage_outputs:
                        dep_context += f"\n[{dep}]:\n{stage_outputs[dep]}\n"
                task = task + dep_context
            
            # Execute this stage
            from claude_agent_sdk import Hooks
            hooks = Hooks(
                pre_tool_use=[self.tracker.pre_tool_use_hook],
                post_tool_use=[self.tracker.post_tool_use_hook]
            )
            
            config = self._create_subagent_config(agent_type, task)
            options = ClaudeAgentOptions(
                cwd=str(self.workspace),
                allowed_tools=config["allowed_tools"],
                permission_mode="acceptEdits",
                hooks=hooks,
                system_prompt=config["system_prompt"]
            )
            
            stage_output = []
            async for message in query(prompt=task, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            stage_output.append(block.text)
            
            # Store output for next stages
            stage_outputs[stage_name] = "\n".join(stage_output)
            print(f"✓ Stage {i+1} complete")
        
        self.tracker.print_summary()
        
        return {
            "status": "completed",
            "stage_outputs": stage_outputs,
            "workspace": str(self.workspace)
        }


async def example_pipeline():
    """
    Example: Multi-stage pipeline with explicit data passing
    """
    orchestrator = PipelineOrchestrator(workspace_dir="./pipeline_workspace")
    
    stages = [
        {
            "name": "data-collection",
            "agent_type": "research-specialist",
            "task": """Search for the top 5 AI companies by market cap in 2025.
            Create a file called companies.md with company names, market caps, and brief descriptions.""",
            "dependencies": []
        },
        {
            "name": "analysis",
            "agent_type": "data-analyst",
            "task": """Read the companies.md file from the previous stage.
            Analyze the data and create a summary comparing these companies.
            Save your analysis to analysis.md""",
            "dependencies": ["data-collection"]
        },
        {
            "name": "report-writing",
            "agent_type": "technical-writer",
            "task": """Read both companies.md and analysis.md from previous stages.
            Create a comprehensive final report that combines all information.
            Save it as final_report.md with proper structure and formatting.""",
            "dependencies": ["data-collection", "analysis"]
        }
    ]
    
    result = await orchestrator.execute_pipeline(stages)
    return result


# ============================================================================
# EXAMPLE 3: Parallel Execution with Synthesis
# ============================================================================

async def example_parallel_research():
    """
    Example: Spawn multiple agents in parallel, then synthesize results
    """
    orchestrator = MultiAgentOrchestrator(workspace_dir="./parallel_workspace")
    
    task = """
    Research renewable energy developments across different sectors.
    
    PARALLEL EXECUTION:
    1. Spawn 3 research agents in parallel (run_in_background: true):
       - Agent 1: Research solar energy developments
       - Agent 2: Research wind energy developments  
       - Agent 3: Research battery storage technologies
    
    2. Each agent should:
       - Search for recent developments
       - Save findings to separate markdown files
    
    3. After all agents complete:
       - Read all their outputs
       - Synthesize into one comprehensive report
       - Save as renewable_energy_report.md
    
    This demonstrates parallel execution and result synthesis.
    """
    
    result = await orchestrator.execute_task(task)
    return result


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """
    Run examples demonstrating different orchestration patterns
    """
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║  Multi-Agent Orchestration with Claude Agent SDK                ║
    ║  Demonstration of Task Decomposition and Agent Coordination      ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Choose which example to run
    examples = {
        "1": ("Simple Research Task", example_research_task),
        "2": ("Multi-Stage Pipeline", example_pipeline),
        "3": ("Parallel Execution", example_parallel_research)
    }
    
    print("Available examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    choice = input("\nSelect example (1-3) or 'all' to run all: ").strip()
    
    if choice == "all":
        for name, func in examples.values():
            print(f"\n\n{'#'*70}")
            print(f"# Running: {name}")
            print(f"{'#'*70}\n")
            await func()
    elif choice in examples:
        name, func = examples[choice]
        await func()
    else:
        print("Invalid choice. Running example 1 by default.")
        await example_research_task()


if __name__ == "__main__":
    # Run the orchestrator
    asyncio.run(main())
