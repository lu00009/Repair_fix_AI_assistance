from langchain_core.tools import tool
from typing import Any
from . import ifixit_client
from .ifixit_client import formatted_result_for_query


FALLBACK_MESSAGE = (
    "It looks like iFixit doesn't have a dedicated step-by-step guide for the back "
    "panel replacement on your specific IdeaPad 1 14IGL7 yet. I can still help — "
    "I can provide a general roadmap and tips for replacing a laptop back panel, "
    "or try to find community-made guides and videos online. Which would you prefer?"
)


@tool
def ifixit_search(query: str) -> str:
    """Tool wrapper that returns a plain-text summary using API+scrape.

    If no device or guides are found, returns a friendly fallback message.
    """
    try:
        device_res = ifixit_client.find_device(query)
        if not device_res.get("found"):
            return FALLBACK_MESSAGE

        device_title = device_res.get("device_title")
        guides_res = ifixit_client.list_guides(device_title)
        if not guides_res.get("found") or not guides_res.get("guides"):
            return FALLBACK_MESSAGE

        guides = guides_res.get("guides", [])
        q_low = query.lower()
        preferred = None
        for g in guides:
            t = (g.get("title") or "").lower()
            if "back" in q_low and "back" in t:
                preferred = g
                break
            if "panel" in q_low and "panel" in t:
                preferred = g
                break
        if not preferred and guides:
            preferred = guides[0]

        guide_detail = ifixit_client.get_guide(preferred.get("guideid"))

        out_lines = []
        out_lines.append(f"Device Found: {'Yes' if device_res.get('found') else 'No'}")
        out_lines.append(f"iFixit Guide Available: {'Yes' if guides else 'No'}")
        out_lines.append("")
        out_lines.append("Guide Title(s):")
        out_lines.append("")
        out_lines.append(preferred.get("title") or "Unknown")
        out_lines.append("")
        out_lines.append("Steps Summary:")
        out_lines.append("")

        steps = guide_detail.get("steps", []) if guide_detail.get("found") else []
        if not steps:
            out_lines.append("Note: No step text available for this guide.")
        else:
            for idx, s in enumerate(steps, 1):
                text = s.get("text", "").strip()
                if text:
                    out_lines.append(f"Step {idx}: {text}")
                else:
                    imgs = s.get("images", [])
                    if imgs:
                        out_lines.append(f"Step {idx}: (no textual instructions available; image provided)")
                    else:
                        out_lines.append(f"Step {idx}: (no textual instructions available)")

        out_lines.append("")
        out_lines.append("Images:")
        images = []
        for s in steps:
            for im in s.get("images", []):
                if im not in images:
                    images.append(im)
        if images:
            for im in images:
                out_lines.append(im)
        else:
            out_lines.append("No images available.")

        out_lines.append("")
        out_lines.append("Tools (from guide):")
        tools = guide_detail.get("tools", [])
        if tools:
            for t in tools:
                out_lines.append(t)
        else:
            out_lines.append("No tools listed.")

        return "\n".join(out_lines)
    except Exception as e:
        return f"Error running iFixit search: {e}"


@tool
def find_device(query: str) -> str:
    """Compatibility wrapper: returns a readable device search result string."""
    try:
        res = ifixit_client.find_device(query)
        # If not found, retry after stripping common repair keywords
        if not res.get("found"):
            import re
            cleaned = re.sub(r"\b(back|panel|replacement|disassembly|battery|fan|replace|repair)\b", "", query, flags=re.I).strip()
            if cleaned and cleaned.lower() != query.lower():
                res = ifixit_client.find_device(cleaned)
        if not res.get("found"):
            return "No results found."
        lines = ["Found devices:"]
        dt = res.get("device_title")
        if dt:
            lines.append(f"- {dt}")
        for m in res.get("matches", [])[:6]:
            title = m.get("title")
            url = m.get("url")
            if title and url:
                lines.append(f"- {title} (URL: {url})")
            elif title:
                lines.append(f"- {title}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error in find_device: {e}"


@tool
def list_guides(device_title: str) -> str:
    """Compatibility wrapper: returns a readable list of guides for a device."""
    try:
        res = ifixit_client.list_guides(device_title)
        if not res.get("found"):
            return "No repair guides found for this device."
        guides = res.get("guides", [])
        if not guides:
            return "No repair guides found for this device."
        lines = ["Available repair guides:"]
        for g in guides[:10]:
            title = g.get("title", "Unknown")
            gid = g.get("guideid", "N/A")
            diff = g.get("difficulty", "Unknown")
            lines.append(f"- [{gid}] {title} (Difficulty: {diff})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error in list_guides: {e}"


@tool
def get_guide(guide_id: int) -> str:
    """Compatibility wrapper: returns cleaned guide details (steps, images, tools)."""
    try:
        res = ifixit_client.get_guide(guide_id)
        if not res.get("found"):
            return "Status: Not Found - Guide does not exist"
        title = res.get("title", "Unknown Guide")
        lines = [f"**{title}**"]
        steps = res.get("steps", [])
        if not steps:
            lines.append("No steps available.")
        else:
            for idx, s in enumerate(steps, 1):
                txt = s.get("text", "").strip()
                if txt:
                    # shorten to first sentence for brevity
                    first = txt.split('\n')[0]
                    lines.append(f"Step {idx}: {first}")
                else:
                    lines.append(f"Step {idx}: (no textual instructions available)")
                imgs = s.get("images", [])
                for im in imgs[:2]:
                    lines.append(im)
        tools = res.get("tools", [])
        if tools:
            lines.append("\nTools Required:")
            for t in tools:
                lines.append(f"- {t}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error in get_guide: {e}"
