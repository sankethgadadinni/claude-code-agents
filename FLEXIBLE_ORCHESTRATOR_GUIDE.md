# Flexible Plugin-Based Orchestrator Guide

## 🎯 Overview

This is a **plugin-based** multi-agent orchestrator that:
- ✅ **No hard-coded agents** - Register any agent dynamically
- ✅ **Task decomposition** - Automatically breaks down complex tasks
- ✅ **Planning mode** - Uses `permission_mode="plan"` to show plans before execution
- ✅ **Configuration-driven** - Define agents via JSON/code
- ✅ **Runtime flexibility** - Add/remove agents on the fly

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Agent Registry                        │
│  (Plugin System - Register any agent)                   │
│                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐      │
│  │  Agent A   │  │  Agent B   │  │  Agent C   │  ... │
│  └────────────┘  └────────────┘  └────────────┘      │
└─────────────────────────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────┐
│            Flexible Orchestrator                        │
│  (Task Decomposition + Planning)                        │
│                                                         │
│  1. Receives task                                       │
│  2. Queries registry for available agents               │
│  3. Decomposes task into subtasks                       │
│  4. Plans execution (permission_mode="plan")            │
│  5. Shows plan to user                                  │
│  6. Executes after approval                             │
└─────────────────────────────────────────────────────────┘
```

---

## 🔌 Plugin System: Agent Registry

### Registering Agents

#### Method 1: Programmatic Registration

```python
from flexible_orchestrator import AgentRegistry, AgentConfig

registry = AgentRegistry()

# Register a custom agent
registry.register(AgentConfig(
    name="my-agent",
    description="Does specialized work",
    tools=["Read", "Write", "WebSearch"],
    capabilities=["research", "analysis"],
    system_prompt="You are a specialist in X. Your job is to..."
))
```

#### Method 2: From JSON Config

```python
# Load agents from agent_config.json
registry = AgentRegistry()
registry.register_from_file("agent_config.json")
```

**agent_config.json format:**
```json
{
  "agents": [
    {
      "name": "agent-name",
      "description": "What this agent does",
      "tools": ["WebSearch", "Write"],
      "capabilities": ["capability1", "capability2"],
      "system_prompt": "You are...",
      "metadata": {
        "version": "1.0",
        "custom_field": "value"
      }
    }
  ]
}
```

#### Method 3: Runtime Registration

```python
# Register agents dynamically during execution
registry = AgentRegistry()
orchestrator = FlexibleOrchestrator(registry)

# Register agent 1
registry.register(AgentConfig(...))
await orchestrator.execute("Task 1")

# Register agent 2 later
registry.register(AgentConfig(...))
await orchestrator.execute("Task 2")  # Now has both agents
```

---

## 📋 Task Decomposition with Planning Mode

### How It Works

```python
orchestrator = FlexibleOrchestrator(agent_registry=registry)

result = await orchestrator.execute(
    task="Create a web application",
    permission_mode="plan"  # ← Enables planning + decomposition
)
```

**What happens:**

1. **Task Analysis**: Orchestrator analyzes the high-level task
2. **Agent Discovery**: Queries registry for available agents
3. **Decomposition**: Breaks task into subtasks
4. **Planning**: Creates execution plan with:
   - Which agent handles each subtask
   - Dependencies between subtasks
   - Expected outputs
   - Parallel vs sequential execution
5. **User Review**: Shows complete plan
6. **Approval Wait**: Waits for user approval
7. **Execution**: Executes plan systematically

### Example Decomposition Flow

**Input Task:**
```
"Create a REST API for a todo app with tests and documentation"
```

**Orchestrator's Decomposition (shown in plan):**

```
TASK DECOMPOSITION:

Subtask 1: API Design
  Agent: api-designer
  Action: Design REST API endpoints and schemas
  Output: api_design.md
  Dependencies: None
  
Subtask 2: Code Implementation
  Agent: code-generator
  Action: Implement the API based on design
  Output: main.py, models.py, routes.py
  Dependencies: Subtask 1
  
Subtask 3: Test Creation
  Agent: qa-tester
  Action: Write unit and integration tests
  Output: test_api.py
  Dependencies: Subtask 2
  
Subtask 4: Documentation
  Agent: technical-writer
  Action: Create API documentation
  Output: README.md, API_DOCS.md
  Dependencies: Subtask 1, 2
  
Subtask 5: Code Review
  Agent: code-reviewer
  Action: Review all code for quality
  Output: review_notes.md
  Dependencies: Subtask 2, 3

EXECUTION STRATEGY:
- Subtask 1 first (no dependencies)
- Subtask 2, 3, 4 in parallel (after Subtask 1)
- Subtask 5 last (after all others)
```

**User approves → Execution begins**

---

## 💡 Creating Custom Agents

### Agent Configuration Fields

```python
AgentConfig(
    name="agent-identifier",           # Unique name (lowercase-with-dashes)
    description="Human readable desc",  # What the agent does
    tools=["Tool1", "Tool2"],          # Which SDK tools it can use
    capabilities=["cap1", "cap2"],     # Tags for discovery
    system_prompt="You are...",        # Instructs agent behavior
    metadata={}                         # Optional extra data
)
```

### Available Tools

Common tools agents can use:
- `"Read"` - Read files
- `"Write"` - Write/create files
- `"Edit"` - Edit existing files
- `"WebSearch"` - Search the web
- `"WebFetch"` - Fetch web pages
- `"Bash"` - Execute shell commands
- `"Task"` - Spawn sub-agents
- `"Glob"` - Find files by pattern

### Agent Design Best Practices

#### ✅ Good Agent Design

```python
AgentConfig(
    name="security-auditor",
    description="Audits code for security vulnerabilities",
    tools=["Read", "Write"],  # Only what it needs
    capabilities=["security", "audit", "vulnerability-detection"],
    system_prompt="""You are a security auditor specializing in web applications.

YOUR PROCESS:
1. Read all code files
2. Identify security vulnerabilities (SQL injection, XSS, etc.)
3. Check for sensitive data exposure
4. Review authentication and authorization
5. Create detailed audit report with severity ratings

Be thorough and provide specific remediation steps."""
)
```

**Why it's good:**
- ✅ Clear, focused responsibility
- ✅ Minimal necessary tools
- ✅ Specific, actionable system prompt
- ✅ Descriptive capabilities for discovery

#### ❌ Poor Agent Design

```python
AgentConfig(
    name="do-everything",
    description="Does stuff",
    tools=["Read", "Write", "Bash", "WebSearch", "Task"],  # Too many!
    capabilities=["general"],  # Not descriptive
    system_prompt="You are a helpful agent."  # Too vague
)
```

**Why it's bad:**
- ❌ No clear specialization
- ❌ Too many tools (security risk)
- ❌ Vague system prompt
- ❌ Not discoverable by capability

---

## 🎮 Usage Examples

### Example 1: Basic Usage

```python
import asyncio
from flexible_orchestrator import (
    AgentRegistry, AgentConfig, FlexibleOrchestrator
)

async def main():
    # Create registry
    registry = AgentRegistry()
    
    # Register agents
    registry.register(AgentConfig(
        name="researcher",
        description="Web research specialist",
        tools=["WebSearch", "Write"],
        capabilities=["research"],
        system_prompt="You research topics and save findings."
    ))
    
    registry.register(AgentConfig(
        name="writer",
        description="Content writer",
        tools=["Read", "Write"],
        capabilities=["writing"],
        system_prompt="You create well-written content."
    ))
    
    # Create orchestrator
    orchestrator = FlexibleOrchestrator(registry)
    
    # Execute with automatic decomposition
    await orchestrator.execute(
        task="Research AI trends and write an article",
        permission_mode="plan"  # Shows plan first
    )

asyncio.run(main())
```

---

### Example 2: Load from Config

```python
# agent_config.json already has agents defined

async def main():
    registry = AgentRegistry()
    registry.register_from_file("agent_config.json")
    
    orchestrator = FlexibleOrchestrator(registry)
    
    # All agents from config are available
    await orchestrator.execute(
        task="Build a full-stack web app with tests",
        permission_mode="plan"
    )
```

---

### Example 3: Dynamic Agent Addition

```python
async def main():
    registry = AgentRegistry()
    orchestrator = FlexibleOrchestrator(registry)
    
    # Start with minimal agents
    registry.register(AgentConfig(
        name="explorer",
        tools=["Read", "Glob"],
        system_prompt="Explore and understand codebases."
    ))
    
    # First task: Explore
    await orchestrator.execute("Analyze this codebase")
    
    # Based on findings, add specialized agents
    registry.register(AgentConfig(
        name="refactorer",
        tools=["Read", "Write"],
        system_prompt="Refactor code for better quality."
    ))
    
    # Second task: Now can use both
    await orchestrator.execute("Refactor based on analysis")
```

---

### Example 4: Capability-Based Discovery

```python
# Find agents by capability
registry = AgentRegistry()
registry.register_from_file("agent_config.json")

# Find all agents that can do testing
testers = registry.find_by_capability("testing")
print(f"Testing agents: {[a.name for a in testers]}")
# Output: ['qa-tester']

# Find all agents that can code
coders = registry.find_by_capability("coding")
print(f"Coding agents: {[a.name for a in coders]}")
# Output: ['code-generator', 'database-architect']
```

---

## 🎛️ Permission Modes

### Using Different Modes

```python
# 1. Plan mode (shows plan first) - RECOMMENDED
await orchestrator.execute(
    task="Complex task",
    permission_mode="plan"
)

# 2. Accept edits (auto-accept file operations)
await orchestrator.execute(
    task="Simple task",
    permission_mode="acceptEdits"
)

# 3. Default (prompt for dangerous operations)
await orchestrator.execute(
    task="Production task",
    permission_mode="default"
)
```

### When to Use Each Mode

| Mode | Use Case |
|------|----------|
| `"plan"` | Complex tasks, learning, critical operations |
| `"acceptEdits"` | Rapid prototyping, trusted operations |
| `"default"` | Production, when you want control |
| `"bypassPermissions"` | Sandboxed environments only |

---

## 🔧 Advanced Features

### Custom Options

```python
await orchestrator.execute(
    task="Your task",
    permission_mode="plan",
    custom_options={
        "max_tokens": 8000,
        "temperature": 0.7,
        "model": "claude-sonnet-4-5-20250929"
    }
)
```

### Agent Metadata

```python
AgentConfig(
    name="my-agent",
    # ... other fields ...
    metadata={
        "version": "2.0",
        "cost_per_task": "low",
        "latency": "fast",
        "custom_setting": "value"
    }
)

# Access metadata
agent = registry.get("my-agent")
print(agent.metadata["version"])
```

### List All Agents

```python
registry = AgentRegistry()
registry.register_from_file("agent_config.json")

print("Available agents:")
for agent_name in registry.list_agents():
    agent = registry.get(agent_name)
    print(f"  • {agent_name}: {agent.description}")
```

---

## 📊 Task Decomposition Patterns

### Pattern 1: Sequential Pipeline

```
Task: "Process data through multiple stages"

Decomposition:
  Step 1 → Step 2 → Step 3 → Step 4
  
Each step depends on the previous one.
```

### Pattern 2: Parallel Execution

```
Task: "Research multiple topics simultaneously"

Decomposition:
       ┌→ Agent A (topic 1)
Lead → ├→ Agent B (topic 2) → Synthesis Agent
       └→ Agent C (topic 3)
       
All research agents run in parallel.
```

### Pattern 3: Hierarchical

```
Task: "Build complex system"

Decomposition:
                Lead
                 │
        ┌────────┼────────┐
        ↓        ↓        ↓
    Frontend Backend Database
        │        │        │
    ┌───┼───┐  ┌─┼─┐   ┌─┼─┐
    ↓   ↓   ↓  ↓ ↓ ↓   ↓ ↓ ↓
   UI  Tests   API Tests Schema Tests
```

---

## 🎯 Best Practices

### 1. Agent Specialization

✅ **DO**: Create focused, specialized agents
```python
# Good: Specific purpose
"security-auditor" - Audits code for vulnerabilities
"performance-optimizer" - Optimizes for speed
```

❌ **DON'T**: Create generic "do everything" agents
```python
# Bad: Too general
"generic-helper" - Does anything
```

### 2. Tool Minimization

✅ **DO**: Give agents only necessary tools
```python
AgentConfig(
    tools=["Read", "Write"]  # Only what's needed
)
```

❌ **DON'T**: Give all tools to every agent
```python
AgentConfig(
    tools=["Read", "Write", "Bash", "WebSearch", "Task"]  # Too many!
)
```

### 3. Clear System Prompts

✅ **DO**: Write specific, actionable prompts
```python
system_prompt="""You are a test engineer.

YOUR PROCESS:
1. Read the code
2. Identify edge cases
3. Write pytest tests
4. Ensure 80%+ coverage

OUTPUT: test_*.py files"""
```

❌ **DON'T**: Write vague prompts
```python
system_prompt="You help with testing."
```

### 4. Use Planning Mode

✅ **DO**: Use `permission_mode="plan"` for complex tasks
```python
await orchestrator.execute(
    task=complex_task,
    permission_mode="plan"  # See decomposition
)
```

### 5. Version Your Agents

✅ **DO**: Track agent versions in metadata
```python
AgentConfig(
    name="analyzer",
    metadata={"version": "2.1.0"}
)
```

---

## 🚀 Quick Start

```python
# 1. Create registry
registry = AgentRegistry()

# 2. Load agents from config
registry.register_from_file("agent_config.json")

# 3. Create orchestrator
orchestrator = FlexibleOrchestrator(registry)

# 4. Execute task with decomposition
await orchestrator.execute(
    task="Your complex task here",
    permission_mode="plan"
)
```

**That's it!** The orchestrator will:
- Query available agents
- Decompose the task
- Create execution plan
- Show plan to you
- Execute after approval

---

## 📚 Additional Resources

- See `flexible_orchestrator.py` for full implementation
- See `agent_config.json` for example agent definitions
- See `correct_plan_mode.py` for permission mode examples

---

**Key Takeaway**: No hard-coded agents! Register any agent, and the orchestrator handles task decomposition and planning automatically using `permission_mode="plan"`.
