from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Core conversation
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: Optional[str]
    
    # Node 1: normalize_input
    user_query: Optional[str]
    normalized_query: Optional[str]
    
    # Node 2: ifixit_search
    ifixit_results: Optional[List[Dict[str, Any]]]
    device_title: Optional[str]
    
    # Node 3: route_results
    ifixit_found: Optional[bool]
    
    # Node 4: web_search_fallback
    web_results: Optional[List[Dict[str, Any]]]
    
    # Node 5: manage_context
    combined_context: Optional[str]
    has_results: Optional[bool]
    
    # Node 6: format_markdown
    format_prompt: Optional[str]
    prompt_tokens: Optional[int]
    
    # Node 7: stream_response
    formatted_response: Optional[str]
    completion_tokens: Optional[int]
    
    # Node 8: usage_analytics
    total_tokens: Optional[int]
