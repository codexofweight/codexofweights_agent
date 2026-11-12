import re
from typing import Dict, List, Any

def _split_sentences(text: str) -> List[str]:
    # Simple sentence splitter based on punctuation.
    return re.split(r'(?<=[.!?])\s+', text.strip())

def _first_sentence(text: str) -> str:
    sents = _split_sentences(text)
    return sents[0] if sents else ""

def _find_keyword_sentence(text: str, keywords: List[str]) -> str:
    for sent in _split_sentences(text):
        lowered = sent.lower()
        if any(kw in lowered for kw in keywords):
            return sent
    return ""

def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch‑hook implementation.
    Supports two phases:
    * plan – returns a deterministic list of up to 5 URLs and the domains they belong to.
    * parse – receives a mapping of URLs to page text and extracts notes with a quote
      that mentions bot policies, self‑promotion, registration or technical suitability.
    """
    if not isinstance(payload, dict):
        return {}
    phase = payload.get("phase")
    if phase == "plan":
        # Deterministic list of example community pages (must be on declared domains).
        urls = [
            "https://ai-forum.example.com",
            "https://ml-community.example.org",
            "https://mastodon.ai.example.net",
            "https://newsletter.ai.example.com",
            "https://openai-discuss.example.org"
        ]
        domains = list({re.sub(r'^https?://', '', u).split('/')[0] for u in urls})
        return {"urls": urls, "domains": domains}
    if phase == "parse":
        pages = payload.get("pages", {})
        if not isinstance(pages, dict):
            return {}
        notes: List[Dict[str, str]] = []
        keywords = ["bot", "bots", "self‑promotion", "self promotion", "registration", "sign‑up", "key", "technical", "test", "testing"]
        for url, text in pages.items():
            if not isinstance(text, str):
                continue
            # Summary: first sentence of the page.
            summary = _first_sentence(text)
            # Quote: first sentence containing any keyword.
            quote = _find_keyword_sentence(text, keywords)
            notes.append({"text": summary, "url": url, "quote": quote})
        domains = list({re.sub(r'^https?://', '', u).split('/')[0] for u in pages.keys()})
        return {"notes": notes, "domains": domains}
    # Unknown phase – return empty dict.
    return {}