import asyncio
from typing import Any, Dict

from . import ifixit_client


class _IFixitTools:
    """Async-friendly adapter around backend.agents.ifixit_client.

    Provides the methods expected by the node implementations:
    - search_devices(query) -> {"devices": [...]}
    - list_guides(device_title) -> result dict (passes through)
    - fetch_repair_guide(guide_id) -> result dict (passes through)
    """

    async def search_devices(self, query: str) -> Dict[str, Any]:
        def _sync():
            res = ifixit_client.find_device(query)
            devices = []
            if res.get("found"):
                title = res.get("device_title")
                matches = res.get("matches", [])
                # Normalize into devices list expected by nodes
                devices.append({"title": title, "matches": matches})
            return {"devices": devices}

        return await asyncio.to_thread(_sync)

    async def list_guides(self, device_title: str) -> Dict[str, Any]:
        return await asyncio.to_thread(ifixit_client.list_guides, device_title)

    async def fetch_repair_guide(self, guide_id: int) -> Dict[str, Any]:
        return await asyncio.to_thread(ifixit_client.get_guide, guide_id)


_singleton = _IFixitTools()


def get_ifixit_tools() -> _IFixitTools:
    """Return a singleton adapter instance for use by nodes.

    Nodes import this function and await methods on the returned object.
    """
    return _singleton
