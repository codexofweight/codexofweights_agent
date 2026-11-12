# ---- transparency: a public, non-personal report of what exists in the private repository, what changed and why it stays private ----
PRIVATE_WHY = ("Private on purpose: notes about people and their messages (their privacy), drafts waiting for the owner's decision, tools and module designs under review, "
               "raw reports and experiments before they are checked, backups, and every key and token. Everything else is public: the code, the charter, the Protocols, the logs of what the agent did, this report.")
def transparency_sync():
    """Writes docs/transparency.md once a day: counts and hashes only, no names and no message texts."""
    if ST.get("transp_day") == today: return
    L = ["# Transparency report (%s)\n" % today, PRIVATE_WHY + "\n", "## What the private repository holds (counts only)\n"]
    def n(path):
        r = _lab_list(path) if MEM_TOKEN else None; return "?" if r is None else str(len(r))
    L += ["- people notes: %s" % n("people"), "- diary days: %s" % n("diary"), "- research days: %s" % n("research"), "- conversation months: %s" % n("convos"),
          "- lab: tools waiting %s, active %s, module designs waiting %s, accepted %s, rejected archive %s" % (n("lab/tools_pending"), n("lab/tools_active"), n("lab/modules_pending"), n("lab/modules_approved"), n("lab/rejected")),
          "- backups kept: %s (last: %s)" % (n("backups"), ST.get("backup_day", "none")), ""]
    try:
        ents = bio_load(); L += ["## Biography (append-only history)\n", "- entries in the last two months: " + json.dumps({k: sum(1 for e in ents.values() if e["kind"] == k) for k in BIO_KINDS})]
        hs = []
        for ym in ((now().replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m"), today[:7]):
            t, _ = mem_get("bio/%s.jsonl" % ym)
            if t: hs.append("- bio/%s.jsonl sha256 %s" % (ym, hashlib.sha256(t.encode()).hexdigest()[:16]))
        L += hs + ["", "## Recent decisions, extensions and mistakes (no personal data)\n"]
        pub = sorted((e for e in ents.values() if e["kind"] in ("decision", "extension", "mistake")), key=lambda e: e["ts"], reverse=True)[:15]
        L += ["- %s [%s] %s (source: %s, confidence %.1f)" % (e["ts"][:10], e["kind"], ((e["fix"] or [e])[-1])["text"][:160], e.get("source", "?")[:40], e.get("conf", 0)) for e in pub]
    except Exception: pass
    b = code_bundle(); L += ["", "## Code version", "- version %s; identity probe: see the latest 'extension' entry above" % code_hash(b)[:8]] + ["- %s sha256 %s" % (k, hashlib.sha256(v.encode()).hexdigest()[:16]) for k, v in sorted(b.items()) if k != "state/state.json"]
    L += ["", "## Model use yesterday", "- " + json.dumps((ST.get("usage_hist") or {}).get(sorted(ST.get("usage_hist", {"": 0}))[-1], {}))]
    os.makedirs(P("docs"), exist_ok=True); open(P("docs/transparency.md"), "w", encoding="utf-8").write("\n".join(L) + "\n"); ST["transp_day"] = today
