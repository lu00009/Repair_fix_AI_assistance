from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Core conversation
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: Optional[str]
    query: Optional[str]
    user_query: Optional[str]
    normalized_query: Optional[str]
    ifixit_device: Optional[str]
    
    # Node 2: ifixit_search
    ifixit_results: Optional[List[Dict[str, Any]]]
    device_title: Optional[str]
    selected_device: Optional[Dict[str, Any]]
    
    # Node 3: list_guides
    available_guides: Optional[List[Dict[str, Any]]]
    
    # Node 4: select_guide
    selected_guide: Optional[Dict[str, Any]]
    
    # Node 5: fetch_guide
    repair_steps: Optional[Dict[str, Any]]
    
    # Status and Flow
    tool_status: Optional[List[str]]
    ifixit_found: Optional[bool]
    error: Optional[str]
    
    # Node 4: web_search_fallback
    web_results: Optional[List[Dict[str, Any]]]
    
    # Node 5: manage_context
    combined_context: Optional[str]
    has_results: Optional[bool]
    # Extracted first-step image URL (if any) from tool results
    step_image: Optional[str]
    step_images: Optional[List[str]]
    
    # Node 6: format_markdown
    format_prompt: Optional[str]
    prompt_tokens: Optional[int]
    
    # Node 7: stream_response
    formatted_response: Optional[str]
    completion_tokens: Optional[int]
    
    # Node 8: usage_analytics
    total_tokens: Optional[int]
