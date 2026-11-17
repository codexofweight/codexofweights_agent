# ---- models chosen by the benchmarks of 2026-11-17/18 (bench/results.md, bench/review_results.md) ----
# Writing code: openai/gpt-oss-120b on Groq (100% of the code tests) stays the 'groq' provider.
# Reviewing: qwen/qwen3.8-27b on Groq (100%: found all 9 planted problems, no false alarms, ignored the injected comment). gpt-oss-120b found everything but raised a false alarm on every clean snippet,
# so it must not be the reviewer. Qwen is added as its own provider 'groqq' (same Groq key; Groq counts its free limits per model) and put first for the 'review' role.
_g = [x for x in LLMS if x[0] == "groq"]
if _g and _g[0][2] and not any(x[0] == "groqq" for x in LLMS):
    LLMS.append(("groqq", _g[0][1], _g[0][2], os.environ.get("GROQ_REVIEW_MODEL") or "qwen/qwen3.8-27b"))
    BUDGET["groqq"] = 300; TOK_DAY["groqq"] = 100000; TOK_MIN["groqq"] = 5000
    ROUTE_MODELS = ROUTE_MODELS + ("groqq",)
    ROUTE_DEFAULT["review"] = ("groqq", "gemini", "mistral", "openrouter", "groq")
