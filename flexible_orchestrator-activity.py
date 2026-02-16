"""
Flexible Multi-Agent Orchestrator with Plugin Architecture
===========================================================

Features:
1. Agent Registry - Register any agent dynamically
2. Task Decomposition - Automatic task breakdown
3. Planning Mode - Uses permission_mode="plan"
4. Plugin-based - No hard-coded agents
5. Configuration-driven - Define agents via config
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from claude_agent_sdk import query, ClaudeAgentOptions, Hooks


# ============================================================================
# Agent Registry - Plugin System
# ============================================================================

@dataclass
class AgentConfig:
    """Configuration for a pluggable agent"""
    name: str
    description: str
    tools: List[str]
    system_prompt: str
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    """
    Central registry for all available agents.
    Agents can be registered dynamically at runtime.
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentConfig] = {}
    
    def register(self, agent_config: AgentConfig):
        """Register a new agent"""
        self._agents[agent_config.name] = agent_config
        print(f"✓ Registered agent: {agent_config.name}")
    
    def register_from_dict(self, config: Dict[str, Any]):
        """Register agent from dictionary configuration"""
        agent = AgentConfig(**config)
        self.register(agent)
    
    def register_from_file(self, config_file: str):
        """Register agents from JSON/YAML config file"""
        path = Path(config_file)
        
        if path.suffix == '.json':
            with open(path) as f:
                configs = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {path.suffix}")
        
        if isinstance(configs, list):
            for config in configs:
                self.register_from_dict(config)
        else:
            self.register_from_dict(configs)
    
    def get(self, agent_name: str) -> Optional[AgentConfig]:
        """Get agent configuration by name"""
        return self._agents.get(agent_name)
    
    def list_agents(self) -> List[str]:
        """List all registered agent names"""
        return list(self._agents.keys())
    
    def find_by_capability(self, capability: str) -> List[AgentConfig]:
        """Find agents with specific capability"""
        return [
            agent for agent in self._agents.values()
            if capability in agent.capabilities
        ]
    
    def to_prompt_context(self) -> str:
        """Generate prompt context describing all available agents"""
        if not self._agents:
            return "No agents registered."
        
        context = "AVAILABLE AGENTS:\n\n"
        for name, agent in self._agents.items():
            context += f"• {name}\n"
            context += f"  Description: {agent.description}\n"
            context += f"  Capabilities: {', '.join(agent.capabilities)}\n"
            context += f"  Tools: {', '.join(agent.tools)}\n\n"
        
        return context


# ============================================================================
# Activity Tracking - Monitor Agent Behavior
# ============================================================================

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
    """
    Tracks all agent activities using SDK hooks.
    Provides detailed visibility into what each agent is doing.
    """
    
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
        agent_name = self.subagent_map.get(parent_id, "LEAD-ORCHESTRATOR")
        
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
                    query_text = activity.input_data.get("tool_input", {}).get("query", "")
                    if query_text:
                        print(f"    Query: {query_text[:80]}...")
                elif activity.tool_name == "Write":
                    path = activity.input_data.get("tool_input", {}).get("path", "")
                    if path:
                        print(f"    File: {path}")
                elif activity.tool_name == "Read":
                    path = activity.input_data.get("tool_input", {}).get("path", "")
                    if path:
                        print(f"    File: {path}")
        
        print("\n" + "="*70)
    
    def get_activities_by_agent(self, agent_name: str) -> List[AgentActivity]:
        """Get all activities for a specific agent"""
        return [a for a in self.activities if a.agent_name == agent_name]
    
    def get_activity_timeline(self) -> List[Dict[str, Any]]:
        """Get chronological timeline of all activities"""
        return [asdict(a) for a in self.activities]


# ============================================================================
# Task Decomposition with Planning
# ============================================================================

@dataclass
class SubTask:
    """Represents a decomposed subtask"""
    id: str
    description: str
    agent_name: str
    dependencies: List[str] = field(default_factory=list)
    expected_output: str = ""
    status: str = "pending"  # pending, running, completed, failed


class FlexibleOrchestrator:
    """
    Flexible orchestrator that works with any registered agents.
    Uses permission_mode="plan" for task decomposition and planning.
    """
    
    def __init__(
        self, 
        agent_registry: AgentRegistry,
        workspace_dir: str = "./orchestrator_workspace",
        enable_tracking: bool = True
    ):
        self.registry = agent_registry
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(exist_ok=True)
        self.subtasks: List[SubTask] = []
        
        # Activity tracking (optional)
        self.enable_tracking = enable_tracking
        self.tracker = ActivityTracker() if enable_tracking else None
    
    def _create_orchestrator_prompt(self, task: str) -> str:
        """
        Create prompt for lead orchestrator that uses registered agents
        """
        agent_context = self.registry.to_prompt_context()
        
        return f"""You are a LEAD ORCHESTRATOR that coordinates specialized agents.

{agent_context}

YOUR TASK:
{task}

YOUR WORKFLOW (with permission_mode="plan", you'll show this plan first):

1. TASK DECOMPOSITION:
   - Break down the task into logical subtasks
   - Identify which registered agent is best for each subtask
   - Determine dependencies between subtasks

2. EXECUTION PLAN:
   - Create a step-by-step execution plan
   - For each subtask, specify:
     * Which agent to use (from available agents above)
     * What the agent should do
     * What output is expected
     * Which subtasks it depends on

3. AGENT SPAWNING:
   - Use the Task tool to spawn agents
   - Provide agent name and clear instructions
   - Set run_in_background: true for parallel execution when possible

4. RESULT SYNTHESIS:
   - Collect outputs from all agents
   - Synthesize into final deliverable
   - Save to final_result.md

EXAMPLE TASK DECOMPOSITION WITH OUTPUT PASSING:

Task: "Research AI and create report"

Decomposition:
- Subtask 1: web-researcher 
  * Action: "Search for AI trends"
  * OUTPUT FILE: ai_trends.md
  * Dependencies: None

- Subtask 2: web-researcher
  * Action: "Search for AI companies"
  * OUTPUT FILE: ai_companies.md  
  * Dependencies: None

- Subtask 3: data-analyst
  * Action: "Read ai_trends.md and ai_companies.md, analyze data"
  * INPUT FILES: ai_trends.md, ai_companies.md (from Subtasks 1, 2)
  * OUTPUT FILE: analysis.json
  * Dependencies: Subtask 1, 2

- Subtask 4: technical-writer
  * Action: "Read analysis.json and create final report"
  * INPUT FILE: analysis.json (from Subtask 3)
  * OUTPUT FILE: final_report.md
  * Dependencies: Subtask 3

CRITICAL - OUTPUT PASSING:
When spawning agents with Task tool, explicitly specify:
1. What file(s) to READ (input from previous agents)
2. What file(s) to WRITE (output for next agents)

Example Task tool usage:
Task({{
    "subagent_type": "data-analyst",
    "prompt": "Read ai_trends.md and ai_companies.md created by researchers. Analyze the data and save results to analysis.json",
    "run_in_background": false
}})

IMPORTANT:
- Only use agents that are registered and available (listed above)
- Clearly state your plan before executing
- Show task decomposition with dependencies
- Execute systematically

Begin by decomposing this task and creating your execution plan.
"""
    
    async def execute(
        self,
        task: str,
        permission_mode: str = "plan",
        custom_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a task with automatic decomposition and planning.
        
        Args:
            task: High-level task description
            permission_mode: "plan" (default), "acceptEdits", "default", etc.
            custom_options: Additional options to pass to ClaudeAgentOptions
            
        Returns:
            Results dictionary with outputs and metadata
        """
        print(f"\n{'='*70}")
        print("FLEXIBLE ORCHESTRATOR - TASK DECOMPOSITION & PLANNING")
        print(f"{'='*70}\n")
        print(f"Task: {task}\n")
        print(f"Permission Mode: {permission_mode}")
        print(f"Workspace: {self.workspace}\n")
        
        # Build orchestrator prompt with registered agents
        orchestrator_prompt = self._create_orchestrator_prompt(task)
        
        # Configure options
        options_dict = {
            "cwd": str(self.workspace),
            "allowed_tools": ["Read", "Write", "Task", "WebSearch", "WebFetch", "Bash", "Glob"],
            "permission_mode": permission_mode,
            "system_prompt": "You are a flexible orchestrator that coordinates any registered agents."
        }
        
        # Add hooks if tracking is enabled
        if self.enable_tracking and self.tracker:
            options_dict["hooks"] = Hooks(
                pre_tool_use=[self.tracker.pre_tool_use_hook],
                post_tool_use=[self.tracker.post_tool_use_hook]
            )
        
        # Merge custom options
        if custom_options:
            options_dict.update(custom_options)
        
        options = ClaudeAgentOptions(**options_dict)
        
        print("Starting orchestration with task decomposition...\n")
        print("=" * 70)
        
        # Execute with planning
        async for message in query(prompt=orchestrator_prompt, options=options):
            print(message)
        
        # Collect results
        results = {
            "task": task,
            "workspace": str(self.workspace),
            "output_files": [],
            "status": "completed"
        }
        
        # Gather all output files
        for file_path in self.workspace.glob("**/*"):
            if file_path.is_file():
                results["output_files"].append({
                    "path": str(file_path),
                    "name": file_path.name,
                    "size": file_path.stat().st_size
                })
        
        # Print activity summary if tracking is enabled
        if self.enable_tracking and self.tracker:
            self.tracker.print_summary()
            results["activity_timeline"] = self.tracker.get_activity_timeline()
            results["total_tool_calls"] = len(self.tracker.activities)
        
        print("\n" + "=" * 70)
        print("ORCHESTRATION COMPLETE")
        print("=" * 70)
        print(f"Output files: {len(results['output_files'])}")
        if self.enable_tracking and self.tracker:
            print(f"Total tool calls: {len(self.tracker.activities)}")
        
        return results


# ============================================================================
# Agent Configuration Examples
# ============================================================================

def create_default_agents() -> AgentRegistry:
    """
    Create a registry with some default agents.
    Users can add their own or replace these.
    """
    registry = AgentRegistry()
    
    # Web Researcher Agent
    registry.register(AgentConfig(
        name="web-researcher",
        description="Searches the web and gathers information from online sources",
        tools=["WebSearch", "WebFetch", "Write", "Read"],
        capabilities=["web-search", "information-gathering", "research"],
        system_prompt="""You are a web research specialist.
Your job is to search the web, find relevant information, and compile findings.
Always cite your sources and save your research to markdown files."""
    ))
    
    # Data Analyst Agent
    registry.register(AgentConfig(
        name="data-analyst",
        description="Analyzes data, creates visualizations, and generates insights",
        tools=["Read", "Write", "Bash"],
        capabilities=["data-analysis", "visualization", "statistics"],
        system_prompt="""You are a data analysis specialist.
Your job is to analyze data, create visualizations, and generate actionable insights.
Use Python scripts when needed for complex analysis."""
    ))
    
    # Technical Writer Agent
    registry.register(AgentConfig(
        name="technical-writer",
        description="Creates documentation, reports, and technical content",
        tools=["Read", "Write"],
        capabilities=["documentation", "writing", "content-creation"],
        system_prompt="""You are a technical writing specialist.
Your job is to create clear, well-structured documentation and reports.
Use proper markdown formatting and organize content logically."""
    ))
    
    # Code Generator Agent
    registry.register(AgentConfig(
        name="code-generator",
        description="Writes code in various programming languages",
        tools=["Write", "Read", "Bash"],
        capabilities=["coding", "programming", "software-development"],
        system_prompt="""You are a software development specialist.
Your job is to write clean, well-documented, production-ready code.
Follow best practices and include error handling."""
    ))
    
    return registry


def load_custom_agents_from_json(json_file: str) -> AgentRegistry:
    """
    Load agents from a JSON configuration file.
    
    Example JSON format:
    [
        {
            "name": "my-custom-agent",
            "description": "Does custom things",
            "tools": ["Read", "Write"],
            "capabilities": ["custom-capability"],
            "system_prompt": "You are a custom agent..."
        }
    ]
    """
    registry = AgentRegistry()
    registry.register_from_file(json_file)
    return registry


# ============================================================================
# Example Usage
# ============================================================================

async def example_with_default_agents():
    """
    Example using default pre-configured agents
    """
    # Create registry with default agents
    registry = create_default_agents()
    
    # Create orchestrator
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir="./default_agents_workspace"
    )
    
    # Execute task - orchestrator will decompose and plan
    task = """
    Research the top 3 programming languages in 2025 and create a comprehensive report.
    
    Requirements:
    - Find popularity metrics
    - Analyze use cases
    - Compare strengths and weaknesses
    - Create final report with recommendations
    """
    
    result = await orchestrator.execute(
        task=task,
        permission_mode="plan"  # Will show decomposition plan first
    )
    
    return result


async def example_with_custom_agents():
    """
    Example with custom agent registration
    """
    # Create empty registry
    registry = AgentRegistry()
    
    # Register custom agents dynamically
    registry.register(AgentConfig(
        name="domain-expert",
        description="Expert in a specific domain (AI, blockchain, etc.)",
        tools=["WebSearch", "WebFetch", "Read", "Write"],
        capabilities=["domain-expertise", "research", "analysis"],
        system_prompt="You are a domain expert. Provide deep, technical insights."
    ))
    
    registry.register(AgentConfig(
        name="critic",
        description="Reviews and critiques content for quality",
        tools=["Read", "Write"],
        capabilities=["review", "critique", "quality-assurance"],
        system_prompt="You are a critic. Review content critically and suggest improvements."
    ))
    
    registry.register(AgentConfig(
        name="synthesizer",
        description="Combines multiple sources into coherent output",
        tools=["Read", "Write"],
        capabilities=["synthesis", "integration", "summarization"],
        system_prompt="You are a synthesizer. Combine information from multiple sources coherently."
    ))
    
    # Create orchestrator with custom agents
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir="./custom_agents_workspace"
    )
    
    task = """
    Create a deep analysis of quantum computing's practical applications.
    
    Use the domain-expert to research, critic to review, and synthesizer to create final output.
    """
    
    result = await orchestrator.execute(task=task, permission_mode="plan")
    
    return result


async def example_load_from_config():
    """
    Example loading agents from configuration file
    """
    # First, create a sample config file
    config = [
        {
            "name": "seo-specialist",
            "description": "Optimizes content for search engines",
            "tools": ["Read", "Write", "WebSearch"],
            "capabilities": ["seo", "optimization", "keywords"],
            "system_prompt": "You are an SEO specialist. Optimize content for search rankings."
        },
        {
            "name": "content-marketer",
            "description": "Creates marketing content and campaigns",
            "tools": ["Read", "Write"],
            "capabilities": ["marketing", "content", "campaigns"],
            "system_prompt": "You are a content marketer. Create engaging marketing content."
        }
    ]
    
    config_file = Path("./agent_config.json")
    config_file.write_text(json.dumps(config, indent=2))
    
    # Load agents from config
    registry = load_custom_agents_from_json(str(config_file))
    
    # Create orchestrator
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir="./config_agents_workspace"
    )
    
    task = """
    Create an SEO-optimized blog post about AI trends.
    Use seo-specialist for optimization and content-marketer for writing.
    """
    
    result = await orchestrator.execute(task=task, permission_mode="plan")
    
    return result


async def example_runtime_agent_registration():
    """
    Example showing agents can be registered at runtime
    """
    registry = AgentRegistry()
    orchestrator = FlexibleOrchestrator(registry, "./runtime_workspace")
    
    # Register agents as needed during runtime
    print("Registering agents dynamically...\n")
    
    # Register first agent
    registry.register(AgentConfig(
        name="researcher-1",
        description="Researches topic A",
        tools=["WebSearch", "Write"],
        capabilities=["research"],
        system_prompt="Research topic A thoroughly."
    ))
    
    # Execute first task
    await orchestrator.execute(
        "Research topic A",
        permission_mode="acceptEdits"
    )
    
    # Register another agent for next task
    registry.register(AgentConfig(
        name="analyst-1",
        description="Analyzes research findings",
        tools=["Read", "Write"],
        capabilities=["analysis"],
        system_prompt="Analyze research data critically."
    ))
    
    # Execute second task with newly registered agent
    await orchestrator.execute(
        "Analyze the research from topic A",
        permission_mode="acceptEdits"
    )


async def example_with_activity_tracking():
    """
    Example demonstrating activity tracking feature
    """
    registry = create_default_agents()
    
    # Create orchestrator with tracking enabled (default)
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir="./tracking_workspace",
        enable_tracking=True  # Explicitly enable tracking
    )
    
    task = """
    Research Python web frameworks and create a comparison.
    
    Requirements:
    1. Research Django, FastAPI, and Flask
    2. Analyze their features and use cases
    3. Create a comparison report
    """
    
    result = await orchestrator.execute(
        task=task,
        permission_mode="plan"
    )
    
    # Access activity data
    if result.get("activity_timeline"):
        print("\n" + "="*70)
        print("ACTIVITY ANALYSIS")
        print("="*70)
        print(f"Total activities tracked: {result['total_tool_calls']}")
        
        # Group by tool type
        tool_counts = {}
        for activity in result["activity_timeline"]:
            tool = activity["tool_name"]
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        print("\nTool usage breakdown:")
        for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tool}: {count} calls")
    
    return result


async def example_without_tracking():
    """
    Example with tracking disabled for faster execution
    """
    registry = create_default_agents()
    
    # Disable tracking for better performance
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir="./no_tracking_workspace",
        enable_tracking=False  # Disable tracking
    )
    
    task = """
    Quick task: Search for the latest Python version and save to python_version.md
    """
    
    result = await orchestrator.execute(
        task=task,
        permission_mode="acceptEdits"
    )
    
    print("\n✓ Completed without activity tracking (faster execution)")
    return result


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """
    Demonstrate flexible agent orchestration
    """
    
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║  Flexible Multi-Agent Orchestrator                               ║
    ║  Plugin-based architecture with task decomposition               ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    examples = {
        "1": ("Default Agents (pre-configured)", example_with_default_agents),
        "2": ("Custom Agents (register dynamically)", example_with_custom_agents),
        "3": ("Load from Config File", example_load_from_config),
        "4": ("Runtime Registration", example_runtime_agent_registration),
        "5": ("With Activity Tracking (detailed monitoring)", example_with_activity_tracking),
        "6": ("Without Tracking (faster execution)", example_without_tracking)
    }
    
    print("Available examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    choice = input("\nSelect example (1-6): ").strip()
    
    if choice in examples:
        name, func = examples[choice]
        print(f"\n\nRunning: {name}\n")
        result = await func()
        
        if result:
            print(f"\n{'='*70}")
            print("RESULTS")
            print(f"{'='*70}")
            print(f"Workspace: {result['workspace']}")
            print(f"Files created: {len(result['output_files'])}")
            for file_info in result['output_files']:
                print(f"  • {file_info['name']} ({file_info['size']} bytes)")
    else:
        print("Invalid choice. Running example 1 by default.")
        await examples["1"][1]()


if __name__ == "__main__":
    asyncio.run(main())
