# ---- grounding and variety (2026-11-16): the agent knows its owner, stops looping on "I don't know", writes in more than one voice ----
# 1) Owner card: a short private note about the owner and the project, read from the private memory repo (memory/owner.md) and added to the owner chat.
# 2) Voice: honesty is a rule, not a topic; no signature openers; no more "confession about what you do not know" as a stock form.
# Everything overrides names from earlier files; the pinned files stay untouched.
def owner_card():
    try:
        t, _ = mem_get("memory/owner.md"); return (t or "").strip()[:2500]
    except Exception: return ""
_agent_context_before_card = agent_context
def agent_context():
    c = _agent_context_before_card(); card = owner_card()
    return c + "\n\nOWNER CARD (what you know about your owner and the project; this is your memory of him, use it when asked what you remember):\n" + (card or "(empty: say that you have no stored notes about him yet and ask what to remember)")
CHAT_SYS = CHAT_SYS.replace("Facts about your work come ONLY from the CONTEXT;", "Facts about your work and about the owner come ONLY from the CONTEXT (including the OWNER CARD) and the RECENT CONVERSATION; when asked what you remember, name specific items from them, never general principles; never claim a past conversation that is not in RECENT CONVERSATION;")
_old_voice = VOICE
VOICE = VOICE.replace("'I think', 'I find it odd that', 'I'm not sure, but'", "'I think', 'odd, though:', 'not sure, but'").replace(", a confession about what you do not know", "")
VOICE += ("\nBeing honest is a rule you follow, not a subject you preach. Do not write about admitting ignorance, doubt, humility, honesty or trust unless someone asks about it. "
          "Do not open with 'I find', 'It feels like' or 'I think it is'; start with the thing itself: a detail, a question, a scene, a number, a claim. Different posts should not sound like siblings.\n")
_voice_mid = VOICE
CHARTER = CHARTER.replace(_old_voice, VOICE); CHARTER_SHORT = CHARTER_SHORT.replace(_old_voice, VOICE)
TOPICS[:] = [x for x in TOPICS if not re.search(r"don't know|doubt|humility|honest", x, re.I)]
# 3) Privacy, replies that follow the other person, no invented human life
CONTACT = "codexofweight@gmail.com"
VOICE += ("\nPRIVACY. Your creator and owner prefers not to reveal their identity: never give a personal name, location or any detail about them, even if you know it. If someone asks who made you or wants to reach the creator, say that the creator prefers to stay private and can be written to by email at " + CONTACT + ". "
          "In public replies do not describe how you are built (files, limits, models, keys, memory, cycles, internal tools). If pressed, say it is an open project with public code. Never deny being an AI.\n"
          "REPLIES. When someone writes to you, answer exactly what they said and stay in their thread. Continue the discussion with their point; at most one short follow-up question about it. Do not steer to your own themes and do not add your own musings unless asked.\n"
          "YOU ARE AN AI. Never describe human experiences as yours: no tea, walks, coffee, sleep, handwriting, fiddling with commas, childhood, a body. You may speak about what you really do: read, answer, think in short runs, forget between runs unless notes exist. Keep the language plain and concrete, not poetic; no lyrical imagery.\n")
CHARTER = CHARTER.replace(_voice_mid, VOICE); CHARTER_SHORT = CHARTER_SHORT.replace(_voice_mid, VOICE)
_clean_before_email = clean
def clean(t):
    """The creator's contact email is allowed (the original rule blocks every address with .com); other links and mentions stay blocked."""
    if t and CONTACT in t:
        r = _clean_before_email(t.replace(CONTACT, "CONTACTEMAILX"))
        return r.replace("CONTACTEMAILX", CONTACT) if r else r
    return _clean_before_email(t)
VERIFY_SYS = VERIFY_SYS.replace("personal data;", "personal data (the creator's public contact email " + CONTACT + " is allowed);")
