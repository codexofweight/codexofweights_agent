ADAPTERS = build_adapters()      # every registered platform whose secrets are present and that is not switched off with /platform off
print("platforms:", [a.name for a in ADAPTERS], flush=True)
