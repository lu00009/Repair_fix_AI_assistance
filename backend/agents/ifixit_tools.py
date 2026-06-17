import asyncio
from typing import Any, Dict

from . import ifixit_client


from langchain_core.tools import tool

@tool
def search_devices(query: str) -> Dict[str, Any]:
    """Search for devices on iFixit."""
    res = ifixit_client.find_device(query)
    devices = []
    if res.get("found"):
        title = res.get("device_title")
        matches = res.get("matches", [])
        # Normalize into devices list expected by nodes
        devices.append({"title": title, "matches": matches})
    return {"devices": devices}

@tool
def list_guides(device_title: str) -> Dict[str, Any]:
    """List available repair guides for a specific iFixit device."""
    return ifixit_client.list_guides(device_title)

@tool
def fetch_repair_guide(guide_id: int) -> Dict[str, Any]:
    """Fetch full details for an iFixit repair guide."""
    return ifixit_client.get_guide(guide_id)


class _IFixitTools:
    """Adapter for nodes to call tools as methods for backward compatibility."""
    async def search_devices(self, query: str) -> Dict[str, Any]:
        return await asyncio.to_thread(search_devices.invoke, {"query": query})

    async def list_guides(self, device_title: str) -> Dict[str, Any]:
        return await asyncio.to_thread(list_guides.invoke, {"device_title": device_title})

    async def fetch_repair_guide(self, guide_id: int) -> Dict[str, Any]:
        return await asyncio.to_thread(fetch_repair_guide.invoke, {"guide_id": guide_id})


_singleton = _IFixitTools()

def get_ifixit_tools() -> _IFixitTools:
    return _singleton
