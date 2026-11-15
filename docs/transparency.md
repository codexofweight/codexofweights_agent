# Transparency report (2026-11-15)

Private on purpose: notes about people and their messages (their privacy), drafts waiting for the owner's decision, tools and module designs under review, raw reports and experiments before they are checked, backups, and every key and token. Everything else is public: the code, the charter, the Protocols, the logs of what the agent did, this report.

## What the private repository holds (counts only)

- people notes: 34
- diary days: 5
- research days: 5
- conversation months: 1
- lab: tools waiting 6, active 4, module designs waiting 0, accepted 0, rejected archive 3
- backups kept: 10 (last: 2026-11-14)

## Biography (append-only history)

- entries in the last two months: {"decision": 1, "promise": 0, "mistake": 0, "extension": 14, "episode": 0}
- bio/2026-11.jsonl sha256 4a916fb8529b3242

## Recent decisions, extensions and mistakes (no personal data)

- 2026-11-14 [decision] Models auto-replaced: openrouter: модель meta-llama/llama-3.3-70b-instruct:free пропала, замену не нашёл (провайдер пока пропускается) (source: agent decision, confidence 0.8)
- 2026-11-14 [extension] Owner approved tool fact_check_guard (source: owner decision in Telegram, confidence 1.0)
- 2026-11-14 [extension] Code version 2d28b194 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-14 [extension] Proposed tool discourse_context_analyzer (text_check) (source: log:tool_proposed@2026-11-14T22:08+00:00, confidence 1.0)
- 2026-11-14 [extension] Code version 48a23c44 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-14 [extension] Proposed tool honesty_monitor (daily) (source: log:tool_proposed@2026-11-14T16:16+00:00, confidence 1.0)
- 2026-11-14 [extension] Code version d8ac409e deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-14 [extension] Code version 8d63a301 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-14 [extension] Code version 44425a6c deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-14 [extension] Code version b11b42c7 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-14 [extension] Owner approved tool trigger_pre_screener (source: owner decision in Telegram, confidence 1.0)
- 2026-11-13 [extension] Code version 1d42bef0 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-13 [extension] Proposed tool fact_check_guard (text_check) (source: log:tool_proposed@2026-11-13T11:20+00:00, confidence 1.0)
- 2026-11-13 [extension] Code version 9cebc42e baseline; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-13 [extension] Proposed tool trigger_pre_screener (text_check) (source: log:tool_proposed@2026-11-13T11:09+00:00, confidence 1.0)

## Code version
- version 2d28b194; identity probe: see the latest 'extension' entry above
- .github/workflows/agent.yml sha256 1efe830f4c3a8484
- CHARTER.md sha256 172ef887b5069d1c
- FACTS.md sha256 cbed9d66752b513d
- README.md sha256 b8da31b359d7e85c
- agent.py sha256 565be75a7792b4a9
- part_01_core.py sha256 b42dc174279b45fe
- part_02_memory.py sha256 97fbefc78859d3a7
- part_03_adapters.py sha256 17508c859e846bcf
- part_04_research.py sha256 351548e6e134a4b2
- part_05_tools_sandbox.py sha256 0a3d3de9f02b4c26
- part_06_owner_chat.py sha256 ceeef38ae61064fa
- part_06a_private_lab.py sha256 d24f110501cb8680
- part_06b_selfmap.py sha256 fd16dcfb444996a4
- part_06c_bio.py sha256 4676c43dd0b7ed95
- part_06d_backup_identity.py sha256 c7096572187ef24b
- part_06e_transparency.py sha256 04882b031b7ad001
- part_06f_housekeeping.py sha256 bfc18b9b61ea07ef
- part_06g_search.py sha256 d0808768b237f2aa
- part_06h_config.py sha256 829afe42e5ec7e9d
- part_06i_projects.py sha256 4c006e461731da2a
- part_06j_health.py sha256 6bcb754598160f37
- part_06k_content.py sha256 bf044056c023373f
- part_06l_voice.py sha256 243ba66f4685e6aa
- part_06m_resilience.py sha256 5fd3bd994ee0e08e
- part_07_main_loop.py sha256 d71e11714e3ff680

## Model use yesterday
- {"calls": {"gemini": 159, "cohere": 5, "openrouter": 2, "groq": 1}, "tokens": {"gemini": 296754, "cohere": 2431, "openrouter": 753, "groq": 892}}
