def run(payload: dict) -> dict:
    text = payload.get('text', '').lower()
    # Heuristics for common hallucination markers or non-grounded language
    triggers = [
        "i am not sure", "i don't know", "it is possible that", 
        "i might be wrong", "perhaps", "speculatively",
        "as an ai language model"
    ]
    
    # Check if the text is suspiciously short or lacks specific entities
    # A very short response is often a sign of a failed retrieval or hallucination
    if len(text) < 20:
        return {"block": True, "reason": "Response too short to be factually grounded."}
    
    # Check for phrases indicating lack of confidence
    for trigger in triggers:
        if trigger in text:
            return {"block": True, "reason": f"Detected uncertainty marker: {trigger}"}
            
    return {"block": False, "reason": ""}