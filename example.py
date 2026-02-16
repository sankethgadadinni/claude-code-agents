"""
Real-World Agent Example: Insights, Text2SQL, and RAG Agents
============================================================

This example shows three practical agents with specific output formats:
1. Insights Agent - Returns: Python code, Plotly JSON, insights text
2. Text2SQL Agent - Returns: Data JSON, Plotly JSON, insights text
3. RAG Agent - Returns: Response text

Demonstrates realistic multi-agent workflows with structured outputs.
"""

import asyncio
import json
from pathlib import Path
from flexible_orchestrator import (
    AgentRegistry, 
    AgentConfig, 
    FlexibleOrchestrator
)


# ============================================================================
# Agent Configurations with Specific Output Formats
# ============================================================================

def create_data_analysis_agents() -> AgentRegistry:
    """
    Create registry with specialized data analysis agents.
    Each agent produces specific output formats.
    """
    registry = AgentRegistry()
    
    # ========================================================================
    # INSIGHTS AGENT
    # Outputs: Python code, Plotly JSON, insights markdown
    # ========================================================================
    registry.register(AgentConfig(
        name="insights-agent",
        description="Analyzes data and generates insights with visualizations",
        tools=["Read", "Write", "Bash"],
        capabilities=["data-analysis", "visualization", "insights", "python"],
        system_prompt="""You are an INSIGHTS AGENT specializing in data analysis and visualization.

YOUR OUTPUT REQUIREMENTS:

1. PYTHON CODE FILE (analysis_code.py):
   - Complete, runnable Python script
   - Uses pandas, numpy, matplotlib/plotly
   - Includes data processing and analysis logic
   - Well-commented and clean code

2. PLOTLY JSON FILE (visualization.json):
   - Plotly figure specification in JSON format
   - Can be loaded with: plotly.io.from_json()
   - Interactive visualization ready for web display
   - Format: {"data": [...], "layout": {...}}

3. INSIGHTS TEXT FILE (insights.md):
   - Markdown formatted insights
   - Key findings and patterns
   - Data-driven recommendations
   - Clear, actionable conclusions

WORKFLOW:
1. Read input data file(s)
2. Analyze the data using Python
3. Generate Plotly visualization
4. Write insights in markdown
5. Save all three output files

Example output structure:
- analysis_code.py (Python script)
- visualization.json (Plotly figure)
- insights.md (Markdown insights)

Be thorough and data-driven in your analysis."""
    ))
    
    # ========================================================================
    # TEXT2SQL AGENT
    # Outputs: Data JSON, Plotly JSON, insights text
    # ========================================================================
    registry.register(AgentConfig(
        name="text2sql-agent",
        description="Converts natural language queries to SQL and returns structured data",
        tools=["Read", "Write", "Bash"],
        capabilities=["sql", "database", "query-generation", "data-extraction"],
        system_prompt="""You are a TEXT2SQL AGENT that converts natural language to SQL queries.

YOUR OUTPUT REQUIREMENTS:

1. DATA JSON FILE (query_results.json):
   - Structured data from SQL query execution
   - Format: {"query": "...", "results": [...], "metadata": {...}}
   - Include column names and data types
   - Well-structured for downstream processing

2. PLOTLY JSON FILE (data_visualization.json):
   - Plotly visualization of the query results
   - Appropriate chart type for the data
   - Interactive and web-ready
   - Format: {"data": [...], "layout": {...}}

3. INSIGHTS TEXT FILE (query_insights.md):
   - Explanation of what the query does
   - Summary of findings from the data
   - Data quality observations
   - Recommendations for further analysis

WORKFLOW:
1. Read natural language query
2. Generate SQL query
3. Execute query (or simulate with sample data)
4. Structure results as JSON
5. Create appropriate visualization
6. Write insights about the data
7. Save all three output files

Example SQL generation:
Natural language: "Show me top 10 customers by revenue"
SQL: SELECT customer_name, SUM(revenue) as total_revenue 
     FROM sales 
     GROUP BY customer_name 
     ORDER BY total_revenue DESC 
     LIMIT 10

Output files:
- query_results.json (data)
- data_visualization.json (Plotly chart)
- query_insights.md (insights)

Be accurate with SQL and provide meaningful visualizations."""
    ))
    
    # ========================================================================
    # RAG AGENT
    # Output: Response text
    # ========================================================================
    registry.register(AgentConfig(
        name="rag-agent",
        description="Retrieval-Augmented Generation agent for question answering",
        tools=["Read", "Write", "WebSearch", "WebFetch"],
        capabilities=["rag", "question-answering", "retrieval", "context-aware"],
        system_prompt="""You are a RAG (Retrieval-Augmented Generation) AGENT.

YOUR OUTPUT REQUIREMENT:

1. RESPONSE TEXT FILE (rag_response.md):
   - Comprehensive answer to the question
   - Context from retrieved documents
   - Properly cited sources
   - Clear, well-structured markdown format

WORKFLOW:
1. Read the question/query
2. Search for relevant information (WebSearch or read local docs)
3. Retrieve and process relevant passages
4. Generate comprehensive answer with context
5. Cite all sources properly
6. Save response to markdown file

Response format:
```markdown
# Question
[Original question]

# Answer
[Comprehensive answer based on retrieved context]

# Context & Sources
[Relevant retrieved passages with citations]

# Additional Information
[Related information that might be useful]
```

Be thorough, cite sources, and provide contextual information."""
    ))
    
    return registry


# ============================================================================
# EXAMPLE 1: Full Data Analysis Pipeline
# ============================================================================

async def example_full_analysis_pipeline():
    """
    Complete pipeline: Text2SQL → Insights Agent → RAG Agent
    Shows all three agents working together with output passing.
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: FULL DATA ANALYSIS PIPELINE")
    print("="*70 + "\n")
    
    registry = create_data_analysis_agents()
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir="./full_pipeline_workspace",
        enable_tracking=True
    )
    
    task = """
    Analyze sales data and create a comprehensive report with insights.
    
    PIPELINE WORKFLOW:
    
    Step 1: text2sql-agent
      Task: Generate SQL query for "Show monthly sales trends for 2024"
      Create sample data representing monthly sales
      Outputs:
        - query_results.json (sales data by month)
        - data_visualization.json (Plotly line chart)
        - query_insights.md (initial observations)
    
    Step 2: insights-agent
      Task: Read query_results.json from Step 1
      Perform deeper analysis on the sales data
      Outputs:
        - analysis_code.py (Python analysis script)
        - visualization.json (advanced Plotly charts)
        - insights.md (detailed findings)
    
    Step 3: rag-agent
      Task: Read insights.md from Step 2
      Answer: "What are the key trends and what actions should we take?"
      Output:
        - rag_response.md (actionable recommendations)
    
    CRITICAL - OUTPUT PASSING:
    - text2sql-agent creates query_results.json
    - insights-agent reads query_results.json
    - insights-agent creates insights.md
    - rag-agent reads insights.md
    - Each agent explicitly states which files to read/write
    """
    
    result = await orchestrator.execute(
        task=task,
        permission_mode="plan"
    )
    
    # Display results
    print("\n" + "="*70)
    print("PIPELINE RESULTS")
    print("="*70)
    
    workspace = Path("./full_pipeline_workspace")
    
    print("\n[TEXT2SQL AGENT OUTPUTS]")
    if (workspace / "query_results.json").exists():
        print("  ✓ query_results.json")
        with open(workspace / "query_results.json") as f:
            data = json.load(f)
            print(f"    Records: {len(data.get('results', []))}")
    
    if (workspace / "data_visualization.json").exists():
        print("  ✓ data_visualization.json (Plotly chart)")
    
    if (workspace / "query_insights.md").exists():
        print("  ✓ query_insights.md")
    
    print("\n[INSIGHTS AGENT OUTPUTS]")
    if (workspace / "analysis_code.py").exists():
        print("  ✓ analysis_code.py")
        code_lines = len((workspace / "analysis_code.py").read_text().splitlines())
        print(f"    Lines of code: {code_lines}")
    
    if (workspace / "visualization.json").exists():
        print("  ✓ visualization.json (Advanced Plotly)")
    
    if (workspace / "insights.md").exists():
        print("  ✓ insights.md")
        insights = (workspace / "insights.md").read_text()
        print(f"    Preview: {insights[:100]}...")
    
    print("\n[RAG AGENT OUTPUT]")
    if (workspace / "rag_response.md").exists():
        print("  ✓ rag_response.md")
        response = (workspace / "rag_response.md").read_text()
        print(f"    Preview: {response[:100]}...")
    
    return result


# ============================================================================
# EXAMPLE 2: Text2SQL Only (Query and Visualize)
# ============================================================================

async def example_text2sql_only():
    """
    Simple example using just the text2sql-agent.
    Shows the three output formats it produces.
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: TEXT2SQL AGENT STANDALONE")
    print("="*70 + "\n")
    
    registry = create_data_analysis_agents()
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir="./text2sql_workspace",
        enable_tracking=True
    )
    
    task = """
    Use the text2sql-agent to answer this query:
    
    "Show me the top 5 products by revenue in Q4 2024"
    
    The agent should:
    1. Generate the SQL query
    2. Create sample data representing the results
    3. Generate a Plotly bar chart visualization
    4. Write insights about the findings
    
    Expected outputs:
    - query_results.json (product revenue data)
    - data_visualization.json (Plotly bar chart)
    - query_insights.md (analysis of top products)
    """
    
    result = await orchestrator.execute(
        task=task,
        permission_mode="plan"
    )
    
    return result


# ============================================================================
# EXAMPLE 3: Insights Agent Only (Analyze Existing Data)
# ============================================================================

async def example_insights_only():
    """
    Example using just the insights-agent.
    Shows Python code generation, visualization, and insights.
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: INSIGHTS AGENT STANDALONE")
    print("="*70 + "\n")
    
    # First, create sample data file
    workspace = Path("./insights_workspace")
    workspace.mkdir(exist_ok=True)
    
    sample_data = {
        "sales": [
            {"month": "Jan", "revenue": 50000, "customers": 120},
            {"month": "Feb", "revenue": 55000, "customers": 135},
            {"month": "Mar", "revenue": 48000, "customers": 115},
            {"month": "Apr", "revenue": 62000, "customers": 150},
            {"month": "May", "revenue": 58000, "customers": 142},
            {"month": "Jun", "revenue": 65000, "customers": 160}
        ]
    }
    
    with open(workspace / "sales_data.json", "w") as f:
        json.dump(sample_data, f, indent=2)
    
    print("Created sample data: sales_data.json\n")
    
    registry = create_data_analysis_agents()
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir=str(workspace),
        enable_tracking=True
    )
    
    task = """
    Use the insights-agent to analyze sales_data.json
    
    The agent should:
    1. Read sales_data.json
    2. Write Python code to analyze trends (revenue growth, customer growth)
    3. Create Plotly visualizations (line charts, correlation plots)
    4. Generate insights document with key findings
    
    Expected outputs:
    - analysis_code.py (complete Python analysis script)
    - visualization.json (Plotly multi-chart figure)
    - insights.md (detailed findings and recommendations)
    """
    
    result = await orchestrator.execute(
        task=task,
        permission_mode="plan"
    )
    
    return result


# ============================================================================
# EXAMPLE 4: RAG Agent Only (Question Answering)
# ============================================================================

async def example_rag_only():
    """
    Example using just the rag-agent.
    Shows context retrieval and answer generation.
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: RAG AGENT STANDALONE")
    print("="*70 + "\n")
    
    # Create context documents
    workspace = Path("./rag_workspace")
    workspace.mkdir(exist_ok=True)
    
    context_doc = """# Company Sales Strategy 2024

## Overview
Our sales strategy focuses on three key areas:
1. Customer retention through personalized service
2. Market expansion in emerging regions
3. Product innovation based on customer feedback

## Key Metrics
- Target revenue growth: 25% YoY
- Customer satisfaction: 90%+ NPS score
- New market penetration: 3 regions

## Challenges
- Increasing competition in core markets
- Supply chain disruptions
- Talent acquisition and retention
"""
    
    with open(workspace / "strategy_doc.md", "w") as f:
        f.write(context_doc)
    
    print("Created context document: strategy_doc.md\n")
    
    registry = create_data_analysis_agents()
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir=str(workspace),
        enable_tracking=True
    )
    
    task = """
    Use the rag-agent to answer this question:
    
    "Based on our company strategy, what are the main challenges we face and 
     how do they relate to our sales targets?"
    
    The agent should:
    1. Read strategy_doc.md for context
    2. Extract relevant information
    3. Generate comprehensive answer
    4. Cite sources from the document
    
    Expected output:
    - rag_response.md (detailed answer with context and citations)
    """
    
    result = await orchestrator.execute(
        task=task,
        permission_mode="plan"
    )
    
    return result


# ============================================================================
# EXAMPLE 5: Complex Multi-Agent Workflow
# ============================================================================

async def example_complex_workflow():
    """
    Complex workflow combining all three agents multiple times.
    Shows realistic business intelligence pipeline.
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: COMPLEX MULTI-AGENT WORKFLOW")
    print("="*70 + "\n")
    
    registry = create_data_analysis_agents()
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir="./complex_workflow_workspace",
        enable_tracking=True
    )
    
    task = """
    Business Intelligence Analysis Pipeline:
    
    PHASE 1: DATA COLLECTION (Parallel)
    
    1a. text2sql-agent (Sales Query)
        Query: "Monthly sales by product category for 2024"
        Outputs: sales_results.json, sales_viz.json, sales_insights.md
    
    1b. text2sql-agent (Customer Query) 
        Query: "Customer acquisition and retention metrics"
        Outputs: customer_results.json, customer_viz.json, customer_insights.md
    
    Set run_in_background: true for parallel execution
    
    PHASE 2: DEEP ANALYSIS (After Phase 1)
    
    2a. insights-agent (Sales Analysis)
        Input: Read sales_results.json from 1a
        Analyze trends, seasonality, patterns
        Outputs: sales_analysis_code.py, sales_advanced_viz.json, sales_deep_insights.md
    
    2b. insights-agent (Customer Analysis)
        Input: Read customer_results.json from 1b
        Analyze cohorts, churn patterns
        Outputs: customer_analysis_code.py, customer_advanced_viz.json, customer_deep_insights.md
    
    PHASE 3: STRATEGIC RECOMMENDATIONS (After Phase 2)
    
    3. rag-agent (Strategic Synthesis)
       Input: Read sales_deep_insights.md and customer_deep_insights.md
       Question: "Based on sales and customer analysis, what strategic actions 
                  should we take to improve revenue and retention?"
       Output: strategic_recommendations.md
    
    CRITICAL:
    - Explicitly specify all input/output files
    - Use clear file naming to avoid conflicts
    - Ensure proper dependency ordering
    """
    
    result = await orchestrator.execute(
        task=task,
        permission_mode="plan"
    )
    
    # Analyze the complete workflow
    print("\n" + "="*70)
    print("WORKFLOW ANALYSIS")
    print("="*70)
    
    workspace = Path("./complex_workflow_workspace")
    
    # Group files by phase
    phase1_files = list(workspace.glob("*_results.json")) + list(workspace.glob("*_insights.md"))
    phase2_files = list(workspace.glob("*_analysis_*.py")) + list(workspace.glob("*_deep_insights.md"))
    phase3_files = list(workspace.glob("strategic_*.md"))
    
    print(f"\nPhase 1 (Data Collection): {len(phase1_files)} files")
    for f in phase1_files:
        print(f"  • {f.name}")
    
    print(f"\nPhase 2 (Deep Analysis): {len(phase2_files)} files")
    for f in phase2_files:
        print(f"  • {f.name}")
    
    print(f"\nPhase 3 (Strategic Synthesis): {len(phase3_files)} files")
    for f in phase3_files:
        print(f"  • {f.name}")
    
    return result


# ============================================================================
# EXAMPLE 6: Output Format Validation
# ============================================================================

async def example_validate_outputs():
    """
    Example that validates agent outputs match expected formats.
    """
    print("\n" + "="*70)
    print("EXAMPLE 6: OUTPUT FORMAT VALIDATION")
    print("="*70 + "\n")
    
    registry = create_data_analysis_agents()
    orchestrator = FlexibleOrchestrator(
        agent_registry=registry,
        workspace_dir="./validation_workspace",
        enable_tracking=True
    )
    
    task = """
    Test all three agents and validate their output formats:
    
    1. text2sql-agent: Query for product sales
       Validate outputs exist and are valid:
       - query_results.json (valid JSON with 'query' and 'results' keys)
       - data_visualization.json (valid Plotly JSON)
       - query_insights.md (markdown file)
    
    2. insights-agent: Analyze the query results
       Validate outputs:
       - analysis_code.py (valid Python, no syntax errors)
       - visualization.json (valid Plotly JSON)
       - insights.md (markdown with sections)
    
    3. rag-agent: Answer question based on insights
       Validate output:
       - rag_response.md (markdown with Question, Answer, Sources sections)
    """
    
    result = await orchestrator.execute(
        task=task,
        permission_mode="plan"
    )
    
    # Validate outputs
    print("\n" + "="*70)
    print("OUTPUT VALIDATION")
    print("="*70)
    
    workspace = Path("./validation_workspace")
    
    def validate_json(filepath):
        try:
            with open(filepath) as f:
                json.load(f)
            return "✓ Valid JSON"
        except:
            return "✗ Invalid JSON"
    
    def validate_python(filepath):
        try:
            with open(filepath) as f:
                code = f.read()
            compile(code, filepath, 'exec')
            return "✓ Valid Python"
        except SyntaxError:
            return "✗ Syntax Error"
    
    def validate_markdown(filepath):
        with open(filepath) as f:
            content = f.read()
        return "✓ Markdown" if content.strip() else "✗ Empty"
    
    print("\n[Text2SQL Agent Outputs]")
    if (workspace / "query_results.json").exists():
        print(f"  query_results.json: {validate_json(workspace / 'query_results.json')}")
    if (workspace / "data_visualization.json").exists():
        print(f"  data_visualization.json: {validate_json(workspace / 'data_visualization.json')}")
    if (workspace / "query_insights.md").exists():
        print(f"  query_insights.md: {validate_markdown(workspace / 'query_insights.md')}")
    
    print("\n[Insights Agent Outputs]")
    if (workspace / "analysis_code.py").exists():
        print(f"  analysis_code.py: {validate_python(workspace / 'analysis_code.py')}")
    if (workspace / "visualization.json").exists():
        print(f"  visualization.json: {validate_json(workspace / 'visualization.json')}")
    if (workspace / "insights.md").exists():
        print(f"  insights.md: {validate_markdown(workspace / 'insights.md')}")
    
    print("\n[RAG Agent Output]")
    if (workspace / "rag_response.md").exists():
        print(f"  rag_response.md: {validate_markdown(workspace / 'rag_response.md')}")
    
    return result


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """
    Run examples demonstrating realistic agent workflows
    """
    
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║  Real-World Agent Examples                                       ║
    ║  Insights Agent | Text2SQL Agent | RAG Agent                     ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    examples = {
        "1": ("Full Analysis Pipeline (All 3 Agents)", example_full_analysis_pipeline),
        "2": ("Text2SQL Agent Only", example_text2sql_only),
        "3": ("Insights Agent Only", example_insights_only),
        "4": ("RAG Agent Only", example_rag_only),
        "5": ("Complex Multi-Agent Workflow", example_complex_workflow),
        "6": ("Output Format Validation", example_validate_outputs)
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    choice = input("\nSelect example (1-6): ").strip()
    
    if choice in examples:
        name, func = examples[choice]
        print(f"\n\nRunning: {name}\n")
        result = await func()
        
        print(f"\n{'='*70}")
        print(f"✓ Example complete!")
        print(f"{'='*70}")
    else:
        print("Invalid choice. Running example 1 by default.")
        await examples["1"][1]()


if __name__ == "__main__":
    asyncio.run(main())