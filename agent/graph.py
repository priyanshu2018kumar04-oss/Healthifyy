"""
LangGraph StateGraph definition — wires all 6 nodes into the Healthify AI pipeline.

Flow:
  START
    → input_processor_node    (compute BMI/BMR/TDEE)
    → health_analyzer_node    (classify risk levels)
    → warning_detector_node   (generate warning alerts)
    → diet_plan_node          (Groq: generate meal plan)
    → workout_plan_node       (Groq: generate exercise plan)
    → [conditional]
         ├─ generate_weekly=True → progress_tracker_node → END
         └─ generate_weekly=False → END
"""

from langgraph.graph import StateGraph, START, END
from agent.state import AgentState
from agent.nodes import (
    input_processor_node,
    health_analyzer_node,
    warning_detector_node,
    diet_plan_node,
    workout_plan_node,
    progress_tracker_node,
)


def _should_generate_weekly(state: AgentState) -> str:
    """Conditional router: generate weekly report or stop."""
    if state.get("generate_weekly", False):
        return "progress_tracker"
    return "__end__"


def build_health_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    # Register all nodes
    builder.add_node("input_processor",  input_processor_node)
    builder.add_node("health_analyzer",  health_analyzer_node)
    builder.add_node("warning_detector", warning_detector_node)
    builder.add_node("diet_plan",        diet_plan_node)
    builder.add_node("workout_plan",     workout_plan_node)
    builder.add_node("progress_tracker", progress_tracker_node)

    # Linear pipeline
    builder.add_edge(START,              "input_processor")
    builder.add_edge("input_processor",  "health_analyzer")
    builder.add_edge("health_analyzer",  "warning_detector")
    builder.add_edge("warning_detector", "diet_plan")
    builder.add_edge("diet_plan",        "workout_plan")

    # Conditional branch at the end
    builder.add_conditional_edges(
        "workout_plan",
        _should_generate_weekly,
        {
            "progress_tracker": "progress_tracker",
            "__end__": END,
        },
    )
    builder.add_edge("progress_tracker", END)

    return builder.compile()


# Singleton graph — compiled once at import time
health_graph = build_health_graph()
