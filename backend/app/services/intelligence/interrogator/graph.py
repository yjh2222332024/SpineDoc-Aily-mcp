"""
SpineDoc Single-Document Interrogation Graph
=============================================
Executes "decompose → harvest → select → synthesize" lifecycle for single documents.
"""

from langgraph.graph import StateGraph, END
from .state import InterrogatorState
from .nodes import (
    decomposer_node,
    harvester_node,
    selector_node,
    synthesizer_node,
)

def create_interrogator_graph():
    """Build the single-document interrogation state graph."""
    workflow = StateGraph(InterrogatorState)

    workflow.add_node("decomposer", decomposer_node)
    workflow.add_node("harvester", harvester_node)
    workflow.add_node("selector", selector_node)
    workflow.add_node("synthesizer", synthesizer_node)

    workflow.set_entry_point("decomposer")

    workflow.add_edge("decomposer", "harvester")
    workflow.add_edge("harvester", "selector")
    workflow.add_edge("selector", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()

# Singleton export
interrogator_graph = create_interrogator_graph()
