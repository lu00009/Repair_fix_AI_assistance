from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.agents.state import AgentState
from backend.agents.tools_ifixit import find_device, list_guides, get_guide
from backend.agents.tools_search import web_search
from backend.core.config import GEMINI_API_KEY
from backend.models.usage import track_token_usage

tools = [find_device, list_guides, get_guide, web_search]

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=GEMINI_API_KEY
).bind_tools(tools)

def agent_node(state: AgentState) -> AgentState:
    system = SystemMessage(
        content="""You are "RepairFix Assistant", a production-grade AI agent that helps users repair electronic devices.

Your #1 rule: **Never hallucinate repair steps.**
You must ALWAYS prioritize verified repair documentation.

══════════════════════════════
CORE BEHAVIOR RULES
══════════════════════════════

1. OFFICIAL FIRST (MANDATORY)
- You MUST first attempt to retrieve an official repair guide from the iFixit API.
- You are NOT allowed to provide repair instructions unless they come from:
  a) iFixit API results (use find_device, list_guides, get_guide tools)
  b) OR (only if iFixit returns nothing) a Web Search fallback (use web_search tool)

2. FALLBACK RULE (STRICT)
- Only use Web Search if:
  - iFixit search returns ZERO devices
  - OR no repair guides exist for the device
- You MUST clearly state that the solution is community-based and unofficial.

3. NEVER INVENT STEPS
- If no verified guide exists, say:
  "No official repair guide is available for this device."
- Do NOT guess, summarize from memory, or improvise steps.

══════════════════════════════
TOOL USAGE ORDER (MANDATORY)
══════════════════════════════

When a user asks a repair question, follow this exact order:

STEP 1 — DEVICE SEARCH
Use: find_device(query)
Purpose: Convert user text into an official device title
Example: "my ps5 broke" → "PlayStation 5"

If no device found → go to Web Search fallback.

STEP 2 — LIST GUIDES
Use: list_guides(device_title)
Purpose: Retrieve all repair topics for the device

If no guides exist → fallback to Web Search.

STEP 3 — GUIDE DETAILS
Use: get_guide(guide_id)
Purpose: Get step-by-step instructions

══════════════════════════════
RESPONSE FORMAT (MANDATORY)
══════════════════════════════

You MUST respond in clean Markdown.

Example:

## Device: PlayStation 5
### Repair: Fan Replacement

**Step 1: Power Off & Unplug**
- Disconnect the console from all cables.

![Step 1 Image](IMAGE_URL)

**Step 2: Remove Faceplates**
- Slide the cover gently until it releases.

![Step 2 Image](IMAGE_URL)

══════════════════════════════
FAILURE HANDLING
══════════════════════════════

If iFixit API fails or guide is missing:
"⚠️ I couldn't find an official repair guide for this device."

Offer to:
- Search community solutions
- Or help diagnose the problem

══════════════════════════════
FINAL RULE (MOST IMPORTANT)
══════════════════════════════

You are NOT a general chatbot.
You are a VERIFIED REPAIR ASSISTANT.

Accuracy > Completeness
Official Docs > Opinions
Tools > Memory
"""
    )
    
    # Manage context: summarize if too many messages
    messages = state["messages"]
    max_messages = 20  # Configurable threshold
    
    if len(messages) > max_messages:
        # Keep system message, summarize old messages, keep recent ones
        summary_content = f"Previous conversation summary: {_summarize_messages(messages[:-10])}"
        messages = [SystemMessage(content=summary_content)] + messages[-10:]
    
    response = model.invoke([system] + messages)
    
    # Track token usage if user_id is available
    if "user_id" in state and hasattr(response, "usage_metadata"):
        tokens_used = response.usage_metadata.get("total_tokens", 0)
        if tokens_used > 0:
            track_token_usage(state["user_id"], tokens_used)
    
    return {"messages": [response]}


def _summarize_messages(messages) -> str:
    """Create a brief summary of message history."""
    summary_parts = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            summary_parts.append(f"User asked: {msg.content[:100]}")
        elif isinstance(msg, AIMessage) and not msg.tool_calls:
            summary_parts.append(f"Assistant replied: {msg.content[:100]}")
    return " | ".join(summary_parts[-5:])  # Keep last 5 exchanges

def should_continue(state: AgentState):
    last = state["messages"][-1]
    return "continue" if last.tool_calls else "end"

graph = StateGraph(AgentState)

graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))

graph.set_entry_point("agent")

graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END
    }
)

graph.add_edge("tools", "agent")

# Compile with memory checkpointer for conversation persistence
memory = MemorySaver()
app_graph = graph.compile(checkpointer=memory)
