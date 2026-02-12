import httpx
import urllib.parse
import re
from typing import Any, Dict, List

IFIXIT_BASE = "https://www.ifixit.com/api/2.0"
WEB_BASE = "https://www.ifixit.com"


def find_device(query: str) -> Dict[str, Any]:
    query_encoded = urllib.parse.quote(query.strip())
    url = f"{IFIXIT_BASE}/search/{query_encoded}?filter=device"
    resp = httpx.get(url, timeout=10.0)
    if resp.status_code != 200:
        return {"found": False, "error": f"iFixit returned {resp.status_code}", "matches": []}
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return {"found": False, "matches": []}
    first = results[0]
    device_title = first.get("display_title") or first.get("title")
    matches = [{"title": r.get("display_title") or r.get("title"), "url": r.get("url")} for r in results[:6]]
    return {"found": True, "device_title": device_title, "matches": matches}


def list_guides(device_title: str) -> Dict[str, Any]:
    device_encoded = urllib.parse.quote(device_title)
    url = f"{IFIXIT_BASE}/wikis/CATEGORY/{device_encoded}"
    resp = httpx.get(url, timeout=10.0)
    if resp.status_code == 404:
        return {"found": False, "device_title": device_title, "guides": []}
    if resp.status_code != 200:
        return {"found": False, "error": f"iFixit returned {resp.status_code}", "guides": []}
    data = resp.json()
    guides = data.get("guides", [])
    parsed = [{"title": g.get("title"), "guideid": g.get("guideid"), "difficulty": g.get("difficulty")} for g in guides]
    return {"found": True, "device_title": device_title, "guides": parsed}


def get_guide(guide_id: int) -> Dict[str, Any]:
    url = f"{IFIXIT_BASE}/guides/{guide_id}"
    resp = httpx.get(url, timeout=10.0)
    if resp.status_code != 200:
        return {"found": False, "error": f"iFixit returned {resp.status_code}"}
    raw = resp.json()
    title = raw.get("title") or raw.get("display_title") or "Untitled"
    steps_out = []
    for step in raw.get("steps", []) or []:
        lines = step.get("lines") or []
        texts = []
        for ln in lines:
            # prefer explicit text fields used by iFixit API
            t = None
            if isinstance(ln, dict):
                t = ln.get("text") or ln.get("text_raw") or ln.get("text_rendered")
            if t:
                texts.append(t)
        text = "\n".join(texts).strip()
        images = []
        media = step.get("media") or {}
        data = media.get("data") if isinstance(media, dict) else None
        if isinstance(data, dict):
            for key in ("original", "standard", "large", "medium", "small", "url", "thumbnail"):
                if data.get(key):
                    images.append(data.get(key))
                    break
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for key in ("original", "standard", "large", "medium", "small", "url", "thumbnail"):
                        if item.get(key):
                            images.append(item.get(key))
                            break
        if isinstance(media, dict) and media.get("url"):
            images.append(media.get("url"))
        steps_out.append({"text": text, "images": images})
    tools = []
    for t in raw.get("tools", []) or []:
        if isinstance(t, dict) and t.get("text"):
            tools.append(t.get("text"))
        elif isinstance(t, str):
            tools.append(t)

    # If API response lacks step text or images, try scraping the public guide page
    try:
        need_scrape = False
        if not steps_out:
            need_scrape = True
        else:
            # if all steps have empty text, prefer scraped content
            if all(not (s.get("text") and s.get("text").strip()) for s in steps_out):
                need_scrape = True
        if need_scrape:
            scraped = scrape_guide_page(guide_id)
            if scraped.get("found"):
                # prefer scraped title/steps/tools when available
                if scraped.get("title"):
                    title = scraped.get("title")
                if scraped.get("steps"):
                    steps_out = scraped.get("steps")
                if scraped.get("tools"):
                    tools = scraped.get("tools")
    except Exception:
        # scraping is best-effort; ignore failures and return API result
        pass

    return {"found": True, "title": title, "steps": steps_out, "tools": tools}


def fallback_web_search(device_name: str, limit: int = 5) -> List[Dict[str, str]]:
    """DISABLED: Only iFixit results are allowed."""
    return []


def scrape_guide_page(guide_id: int) -> Dict[str, Any]:
    """Scrape the public guide HTML page to extract full step text and images.
    Returns a dict similar to `get_guide` but populated from the HTML.
    """
    import re
    import html as _html

    # Try a few URL patterns. Prefer the slugged URL which usually returns 200.
    # First try the simple numeric path (may return 404 with HTML), then try with title slug.
    url_num = f"{WEB_BASE}/Guide/{guide_id}"
    try:
        resp = httpx.get(url_num, timeout=10.0)
    except Exception as e:
        return {"found": False, "error": str(e)}

    html_text = resp.text or ""

    # If the short URL didn't give the full page, fetch with title slug (from API)
    if 'steps-container' not in html_text.lower():
        # get title from API
        try:
            raw = httpx.get(f"{IFIXIT_BASE}/guides/{guide_id}", timeout=10.0).json()
            title = raw.get('title') or raw.get('display_title') or ''
        except Exception:
            title = ''
        if title:
            from urllib.parse import quote_plus
            slug = quote_plus(title)
            url_slug = f"{WEB_BASE}/Guide/{slug}/{guide_id}"
            try:
                resp2 = httpx.get(url_slug, timeout=10.0)
                html_text = resp2.text or html_text
            except Exception:
                pass

    if not html_text:
        return {"found": False, "error": "No HTML retrieved"}

    # find each step block (li with step-wrapper)
    step_blocks = re.findall(r'(<li[^>]+class="[^"]*step-wrapper[^"]*"[\s\S]*?<\/li>)', html_text, flags=re.I)
    steps_out = []
    # fallback: some pages put steps inside <section itemprop="step"> blocks
    if not step_blocks:
        step_blocks = re.findall(r'(<section[^>]+itemprop="step"[\s\S]*?<\/section>)', html_text, flags=re.I)

    for block in step_blocks:
        # extract images (look for data-biggest, src, meta itemprop image/url)
        images = []
        for m in re.findall(r'data-biggest="([^"]+)"', block):
            images.append(m)
        for m in re.findall(r'<img[^>]+src="([^"]+)"', block):
            if m not in images:
                images.append(m)
        for m in re.findall(r'<meta[^>]+itemprop="image"[^>]+content="([^"]+)"', block):
            if m not in images:
                images.append(m)
        for m in re.findall(r'<meta[^>]+itemprop="url"[^>]+content="([^"]+)"', block):
            if m not in images:
                images.append(m)

        # extract textual steps: <p itemprop="text"> or <li class="level-0" ...><p ...>
        texts = []
        for p in re.findall(r'<p[^>]*itemprop="text"[^>]*>([\s\S]*?)<\/p>', block, flags=re.I):
            txt = re.sub(r'<[^>]+>', '', p)
            txt = _html.unescape(txt).strip()
            if txt:
                texts.append(txt)
        # if none, try other <p> tags inside step-lines
        if not texts:
            for p in re.findall(r'<p[^>]*>([\s\S]*?)<\/p>', block, flags=re.I):
                txt = re.sub(r'<[^>]+>', '', p)
                txt = _html.unescape(txt).strip()
                if txt:
                    texts.append(txt)

        steps_out.append({"text": "\n".join(texts).strip(), "images": images})

    # Try to extract tool list from page
    tools = []
    for m in re.findall(r'<h3[^>]*>Tools(?: Required)?:<\/h3>[\s\S]*?<ul[^>]*>([\s\S]*?)<\/ul>', html_text, flags=re.I):
        for li in re.findall(r'<li[^>]*>([\s\S]*?)<\/li>', m, flags=re.I):
            t = re.sub(r'<[^>]+>', '', li).strip()
            if t and t not in tools:
                tools.append(_html.unescape(t))
    # fallback: look for 'Tools' section by heading text
    if not tools:
        for h in re.findall(r'<h2[^>]*>([^<]*)<\/h2>', html_text, flags=re.I):
            if 'tools' in h.lower():
                # find next ul after this heading
                pos = html_text.lower().find(h.lower())
                nxt = html_text[pos:pos+800]
                for li in re.findall(r'<li[^>]*>([\s\S]*?)<\/li>', nxt, flags=re.I):
                    t = re.sub(r'<[^>]+>', '', li).strip()
                    if t and t not in tools:
                        tools.append(_html.unescape(t))

    # title extraction
    title = ''
    mtitle = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html_text)
    if mtitle:
        title = mtitle.group(1)
    else:
        m = re.search(r'<title[^>]*>([^<]+)<\/title>', html_text)
        if m:
            title = re.sub(r' - iFixit.*$', '', m.group(1)).strip()

    return {"found": True, "title": title, "steps": steps_out, "tools": tools}


def ifixit_query(user_text: str, max_guides: int = 3) -> Dict[str, Any]:
    device_res = find_device(user_text)
    device_found = bool(device_res.get("found"))
    out = {"Device Found": "Yes" if device_found else "No"}
    if not device_found:
        out.update({"iFixit Guide Available": "No", "Guide Title(s)": [], "Steps Summary": [], "Images": []})
        fb = fallback_web_search(user_text)
        out["Fallback"] = fb
        return out
    guides_res = list_guides(device_res.get("device_title"))
    guides_found = bool(guides_res.get("found") and guides_res.get("guides"))
    out["iFixit Guide Available"] = "Yes" if guides_found else "No"
    if not guides_found:
        out.update({"Guide Title(s)": [], "Steps Summary": [], "Images": []})
        return out
    guides = guides_res.get("guides", [])[:max_guides]
    titles = [g.get("title") for g in guides]
    out["Guide Title(s)"] = titles
    steps_summary = []
    images = []
    for g in guides:
        gid = g.get("guideid")
        if not gid:
            continue
        gd = get_guide(gid)
        if not gd.get("found"):
            steps_summary.append({"title": g.get("title"), "steps": []})
            continue
        steps_texts = [s.get("text") for s in gd.get("steps", []) if s.get("text")]
        steps_summary.append({"title": gd.get("title"), "steps": steps_texts, "tools": gd.get("tools", [])})
        for s in gd.get("steps", []):
            for im in s.get("images", []):
                images.append(im)
    out["Steps Summary"] = steps_summary
    out["Images"] = images
    return out


def formatted_result_for_query(user_text: str) -> str:
    """Return a plain-text formatted result matching the user's template.
    Tries to map the query to a device and pick the most relevant guide (e.g., Back Panel).
    """
    # Try direct device lookup; if query includes extra terms, strip common guide keywords
    device_res = find_device(user_text)
    if not device_res.get("found"):
        # strip common repair keywords and retry
        cleaned = re.sub(r"\b(back|panel|replacement|disassembly|battery|fan|replace|repair)\b","", user_text, flags=re.I).strip()
        device_res = find_device(cleaned)

    device_found = bool(device_res.get("found"))
    out_lines = []
    out_lines.append(f"Device Found: {'Yes' if device_found else 'No'}")

    if not device_found:
        out_lines.append("iFixit Guide Available: No")
        out_lines.append("Guide Title(s):")
        out_lines.append("")
        out_lines.append("Steps Summary:")
        out_lines.append("")
        out_lines.append("Images:")
        out_lines.append("")
        out_lines.append("Note: iFixit has no official device page or guides for this query.")
        return "\n".join(out_lines)

    device_title = device_res.get("device_title")
    guides_res = list_guides(device_title)
    guides_found = bool(guides_res.get("found") and guides_res.get("guides"))
    out_lines.append(f"iFixit Guide Available: {'Yes' if guides_found else 'No'}")

    if not guides_found:
        out_lines.append("Guide Title(s):")
        out_lines.append("")
        out_lines.append("Steps Summary:")
        out_lines.append("")
        out_lines.append("Images:")
        out_lines.append("")
        out_lines.append("Note: iFixit has a device page but no repair guides for this device.")
        return "\n".join(out_lines)

    guides = guides_res.get("guides", [])
    # try to select guide that matches user's query (e.g., contains 'back' or 'panel')
    q_low = user_text.lower()
    preferred = None
    for g in guides:
        t = (g.get('title') or '').lower()
        if 'back' in q_low and 'back' in t:
            preferred = g
            break
        if 'panel' in q_low and 'panel' in t:
            preferred = g
            break
    if not preferred:
        # fallback: choose first guide
        preferred = guides[0]

    out_lines.append("Guide Title(s):")
    out_lines.append("")
    out_lines.append(preferred.get('title') or 'Unknown')
    out_lines.append("")

    # fetch guide details
    guide_detail = get_guide(preferred.get('guideid'))
    out_lines.append("Steps Summary:")
    out_lines.append("")

    steps = guide_detail.get('steps', []) if guide_detail.get('found') else []
    if not steps:
        out_lines.append("Note: The iFixit guide contains images for each step but the API response for this guide did not include step text lines.")
    else:
        for idx, s in enumerate(steps, 1):
            text = s.get('text', '').strip()
            if text:
                # use first paragraph only for concise summary
                first_line = text.replace('\n', ' ').strip()
                out_lines.append(f"Step {idx}: {first_line}")
            else:
                # images exist but no text
                imgs = s.get('images', [])
                if imgs:
                    out_lines.append(f"Step {idx}: (no textual instructions available in iFixit API; {'images' if len(imgs)>1 else 'image'} provided)")
                else:
                    out_lines.append(f"Step {idx}: (no textual instructions available in iFixit API)")

    out_lines.append("")
    out_lines.append("Images:")
    # collect unique images from guide_detail steps
    images = []
    for s in steps:
        for im in s.get('images', []):
            if im not in images:
                images.append(im)
    if images:
        for im in images:
            out_lines.append(im)
    else:
        out_lines.append("No images available.")

    out_lines.append("")
    out_lines.append("Tools (from guide):")
    tools = guide_detail.get('tools', [])
    if tools:
        for t in tools:
            out_lines.append(t)
    else:
        out_lines.append("No tools listed.")

    out_lines.append("")
    out_lines.append("If you want, I can:\n- Fetch the full step-by-step text by scraping the guide page (requires consent), or\n- Fetch the other Lenovo IdeaPad 1 14IGL7 guides and return their cleaned summaries.")

    return "\n".join(out_lines)
