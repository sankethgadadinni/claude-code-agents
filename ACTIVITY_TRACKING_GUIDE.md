# Activity Tracking Guide

## Overview

The `ActivityTracker` provides detailed visibility into what each agent is doing during orchestration. It tracks:
- Every tool call made by each agent
- When each action occurred (timestamp)
- What inputs were provided
- What outputs were produced
- Parent-child relationships between agents

## Features

### 1. **Automatic Agent Detection**
Automatically identifies which agent made each tool call:
```
[LEAD-ORCHESTRATOR] - Main coordinator
[WEB-RESEARCHER-1] - First web researcher agent
[DATA-ANALYST-1] - First data analyst agent
```

### 2. **Tool Call Tracking**
Tracks all tool usage:
- `WebSearch` - What queries were made
- `Write` - What files were created
- `Read` - What files were accessed
- `Task` - What subagents were spawned
- `Bash` - What commands were executed

### 3. **Timeline View**
Chronological record of all activities for debugging and analysis.

### 4. **Activity Summaries**
Human-readable summaries grouped by agent.

---

## Usage

### Basic Usage (Tracking Enabled by Default)

```python
from flexible_orchestrator import AgentRegistry, FlexibleOrchestrator, create_default_agents

# Tracking is enabled by default
registry = create_default_agents()
orchestrator = FlexibleOrchestrator(
    agent_registry=registry,
    workspace_dir="./workspace"
    # enable_tracking=True is the default
)

result = await orchestrator.execute(
    task="Your task here",
    permission_mode="plan"
)

# Activity summary is automatically printed
# Activity data is in result["activity_timeline"]
```

---

### Disable Tracking (For Better Performance)

```python
# Disable tracking for faster execution
orchestrator = FlexibleOrchestrator(
    agent_registry=registry,
    workspace_dir="./workspace",
    enable_tracking=False  # Disable tracking
)

result = await orchestrator.execute(
    task="Your task here",
    permission_mode="acceptEdits"
)
# No activity tracking overhead
```

---

### Accessing Activity Data

```python
result = await orchestrator.execute(task="...", permission_mode="plan")

# Check if tracking was enabled
if "activity_timeline" in result:
    print(f"Total tool calls: {result['total_tool_calls']}")
    
    # Access full timeline
    timeline = result["activity_timeline"]
    
    # Each activity has:
    # - agent_name: Which agent made the call
    # - tool_name: What tool was used
    # - timestamp: When it happened
    # - input_data: What was passed to the tool
    # - output_data: What the tool returned
    
    for activity in timeline:
        print(f"{activity['timestamp']}: {activity['agent_name']} used {activity['tool_name']}")
```

---

### Direct Tracker Access

```python
orchestrator = FlexibleOrchestrator(registry, "./workspace")

await orchestrator.execute(task="...", permission_mode="plan")

# Access the tracker directly
if orchestrator.tracker:
    # Print summary
    orchestrator.tracker.print_summary()
    
    # Get activities for specific agent
    lead_activities = orchestrator.tracker.get_activities_by_agent("LEAD-ORCHESTRATOR")
    print(f"Lead agent made {len(lead_activities)} tool calls")
    
    # Get full timeline
    timeline = orchestrator.tracker.get_activity_timeline()
```

---

## Activity Summary Output

When tracking is enabled, you'll see output like:

```
======================================================================
AGENT ACTIVITY SUMMARY
======================================================================

[LEAD-ORCHESTRATOR] - 5 tool calls
  → Task
  → Task
  → Read
  → Write

[WEB-RESEARCHER-1] - 8 tool calls
  → WebSearch
    Query: Python web frameworks 2025...
  → WebFetch
  → Write
    File: frameworks.md

[DATA-ANALYST-1] - 6 tool calls
  → Read
    File: frameworks.md
  → Bash
  → Write
    File: analysis.json

[TECHNICAL-WRITER-1] - 4 tool calls
  → Read
    File: analysis.json
  → Write
    File: final_report.md

======================================================================
```

---

## Use Cases

### 1. **Debugging**
See exactly what each agent did and in what order:
```python
result = await orchestrator.execute(task="...", permission_mode="plan")

# Find where something went wrong
for activity in result["activity_timeline"]:
    if activity["tool_name"] == "WebSearch":
        print(f"Search query: {activity['input_data']['tool_input']['query']}")
```

### 2. **Performance Analysis**
Understand which agents do the most work:
```python
# Count tool calls per agent
agent_counts = {}
for activity in result["activity_timeline"]:
    agent = activity["agent_name"]
    agent_counts[agent] = agent_counts.get(agent, 0) + 1

print("Tool calls per agent:")
for agent, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {agent}: {count}")
```

### 3. **Audit Trail**
Keep records of what agents did:
```python
# Save timeline to file for audit
import json

result = await orchestrator.execute(task="...", permission_mode="plan")

with open("audit_log.json", "w") as f:
    json.dump(result["activity_timeline"], f, indent=2)
```

### 4. **Understanding Agent Behavior**
Learn how agents approach tasks:
```python
# See what tools each agent uses
for activity in result["activity_timeline"]:
    print(f"{activity['agent_name']} → {activity['tool_name']}")
```

---

## Performance Considerations

### Tracking Overhead

Activity tracking adds minimal overhead:
- ~1-2% performance impact
- Small memory footprint (tracking data structures)
- No impact on agent quality

### When to Disable Tracking

Disable tracking when:
- ✅ Running in production with high volume
- ✅ Performance is critical
- ✅ You don't need audit trails
- ✅ Simple, well-tested workflows

Keep tracking enabled when:
- ✅ Developing and debugging
- ✅ Learning how agents work
- ✅ Need audit trails
- ✅ Analyzing agent performance
- ✅ Complex workflows

---

## Advanced Usage

### Custom Activity Analysis

```python
def analyze_agent_efficiency(timeline):
    """Analyze how efficiently agents work"""
    
    # Time between activities
    times = [activity["timestamp"] for activity in timeline]
    
    # Tool usage patterns
    tool_sequences = []
    for i in range(len(timeline) - 1):
        tool_sequences.append((
            timeline[i]["tool_name"],
            timeline[i+1]["tool_name"]
        ))
    
    # Find most common patterns
    from collections import Counter
    patterns = Counter(tool_sequences)
    
    print("Most common tool sequences:")
    for (tool1, tool2), count in patterns.most_common(5):
        print(f"  {tool1} → {tool2}: {count} times")

# Use it
result = await orchestrator.execute(task="...", permission_mode="plan")
analyze_agent_efficiency(result["activity_timeline"])
```

### Filter Activities by Tool

```python
def get_all_searches(timeline):
    """Get all web searches performed"""
    searches = []
    for activity in timeline:
        if activity["tool_name"] == "WebSearch":
            query = activity["input_data"]["tool_input"]["query"]
            searches.append({
                "agent": activity["agent_name"],
                "query": query,
                "time": activity["timestamp"]
            })
    return searches

searches = get_all_searches(result["activity_timeline"])
print(f"Total searches: {len(searches)}")
for search in searches:
    print(f"  {search['agent']}: {search['query']}")
```

### Track File Operations

```python
def get_file_operations(timeline):
    """Track all file read/write operations"""
    files = {"read": [], "write": []}
    
    for activity in timeline:
        if activity["tool_name"] in ["Read", "Write"]:
            path = activity["input_data"]["tool_input"].get("path", "")
            if path:
                files[activity["tool_name"].lower()].append({
                    "agent": activity["agent_name"],
                    "file": path,
                    "time": activity["timestamp"]
                })
    
    return files

files = get_file_operations(result["activity_timeline"])
print(f"Files written: {len(files['write'])}")
print(f"Files read: {len(files['read'])}")
```

---

## Integration with Hooks

The activity tracker uses the SDK's hook system:

```python
from claude_agent_sdk import Hooks

# Hooks are automatically created when tracking is enabled
# You can also add your own custom hooks:

def my_custom_hook(input_data, tool_use_id, context):
    print(f"Custom: About to use {input_data['tool_name']}")
    return {}

# Add custom hooks alongside tracking
orchestrator = FlexibleOrchestrator(registry, "./workspace")

result = await orchestrator.execute(
    task="...",
    permission_mode="plan",
    custom_options={
        "hooks": Hooks(
            pre_tool_use=[
                orchestrator.tracker.pre_tool_use_hook,  # Tracking hook
                my_custom_hook  # Your custom hook
            ]
        )
    }
)
```

---

## Best Practices

### 1. **Keep Tracking Enabled During Development**
```python
# Development
orchestrator = FlexibleOrchestrator(
    registry,
    workspace_dir="./dev_workspace",
    enable_tracking=True  # Keep enabled
)
```

### 2. **Save Activity Logs for Complex Tasks**
```python
result = await orchestrator.execute(task="...", permission_mode="plan")

# Save for later analysis
import json
from datetime import datetime

log_file = f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(log_file, "w") as f:
    json.dump(result["activity_timeline"], f, indent=2)

print(f"Activity log saved to {log_file}")
```

### 3. **Use Summary for Quick Debugging**
```python
# The summary is automatically printed, but you can also:
if orchestrator.tracker:
    orchestrator.tracker.print_summary()  # Print again if needed
```

### 4. **Analyze Tool Usage Patterns**
```python
# Understand which tools are used most
tool_counts = {}
for activity in result["activity_timeline"]:
    tool = activity["tool_name"]
    tool_counts[tool] = tool_counts.get(tool, 0) + 1

print("Tool usage:")
for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {tool}: {count}")
```

---

## Troubleshooting

### Activity Summary Not Showing?

Check if tracking is enabled:
```python
if orchestrator.enable_tracking:
    print("Tracking is enabled")
else:
    print("Tracking is disabled")
```

### Empty Activity Timeline?

Ensure the task actually executed:
```python
result = await orchestrator.execute(task="...", permission_mode="plan")
if result["status"] == "completed":
    if result.get("total_tool_calls", 0) == 0:
        print("No tool calls were made - check your task")
```

### Missing Some Activities?

Hooks are only called for tools in `allowed_tools`:
```python
# Make sure the tool is allowed
orchestrator = FlexibleOrchestrator(
    registry,
    workspace_dir="./workspace",
    custom_options={
        "allowed_tools": ["Read", "Write", "WebSearch", "Bash", "Task"]
    }
)
```

---

## Summary

The ActivityTracker gives you:
- ✅ Complete visibility into agent behavior
- ✅ Debugging capabilities
- ✅ Performance analysis
- ✅ Audit trails
- ✅ Understanding of agent workflows

**Enable it for development, disable it for production if performance matters!**
