from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (aggregate, analyze_diff, bug_analysis, decide_verdict, load_pr,
                             quality_analysis, security_analysis)
from app.agent.state import ReviewState


def build_graph():
    g = StateGraph(ReviewState)
    # Node names must not be the same as a state key, so the last two are named differently.
    g.add_node("load_pr", load_pr)
    g.add_node("analyze_diff", analyze_diff)
    g.add_node("bug_analysis", bug_analysis)
    g.add_node("security_analysis", security_analysis)
    g.add_node("quality_analysis", quality_analysis)
    g.add_node("aggregate", aggregate)
    g.add_node("decide_verdict", decide_verdict)

    g.add_edge(START, "load_pr")
    g.add_edge("load_pr", "analyze_diff")
    g.add_edge("analyze_diff", "bug_analysis")
    g.add_edge("bug_analysis", "security_analysis")
    g.add_edge("security_analysis", "quality_analysis")
    g.add_edge("quality_analysis", "aggregate")
    g.add_edge("aggregate", "decide_verdict")
    g.add_edge("decide_verdict", END)
    return g.compile()


graph = build_graph()


def run_graph(initial_state):
    return graph.invoke(initial_state)
