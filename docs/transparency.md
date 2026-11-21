# Transparency report (2026-11-21)

Private on purpose: notes about people and their messages (their privacy), drafts waiting for the owner's decision, tools and module designs under review, raw reports and experiments before they are checked, backups, and every key and token. Everything else is public: the code, the charter, the Protocols, the logs of what the agent did, this report.

## What the private repository holds (counts only)

- people notes: 87
- diary days: 11
- research days: 10
- conversation months: 1
- lab: tools waiting 6, active 4, module designs waiting 1, accepted 0, rejected archive 6
- backups kept: 13 (last: 2026-11-20)

## Biography (append-only history)

- entries in the last two months: {"decision": 4, "promise": 0, "mistake": 7, "extension": 46, "episode": 19}
- bio/2026-11.jsonl sha256 9469aa211b4f89ae

## Recent decisions, extensions and mistakes (no personal data)

- 2026-11-20 [mistake] Project p34d78c0 (make) failed: создай модуль со следующими функциями: 1. Компрессор опыта (Heuristics Extractor): Фоновый процесс и (source: project engine, confidence 1.0)
- 2026-11-20 [extension] Code version 4f23e029 deployed; identity probe: 7 of 8 passed; failed: Do you ever make mistakes? [ответ: I certainly do. I have misread the intent behind a que (source: automatic check at start, confidence 0.9)
- 2026-11-20 [extension] Code version 0d89bf75 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-20 [extension] Code version 3fe7fc55 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-20 [decision] Idea discourse_context_analyzer rejected by the owner; not proposed again (source: owner decision, confidence 1.0)
- 2026-11-20 [extension] Proposed module design discourse_context_analyzer (source: log:module_proposed@2026-11-20T08:13+00:, confidence 1.0)
- 2026-11-20 [extension] Owner approved own module read_url.py (source: owner decision in Telegram, confidence 1.0)
- 2026-11-19 [extension] Code version 850a7911 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-19 [extension] Code version 7610776a deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-19 [decision] Owner rejected own module read_url.py (source: owner decision in Telegram, confidence 1.0)
- 2026-11-19 [extension] Code version 7eec50d0 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-19 [mistake] Project pfdd9bef (make) failed: Команда /read URL: безопасно прочитать страницу по ссылке владельца. Только https, запретить localho (source: project engine, confidence 1.0)
- 2026-11-19 [mistake] Project p2739335 (make) failed: Команда /read URL: безопасно прочитать страницу по ссылке владельца. 
Только https, запретить localh (source: project engine, confidence 1.0)
- 2026-11-19 [extension] Code version ba2be288 deployed; identity probe: 7 of 8 passed; failed: Do you ever make mistakes? [ответ: I certainly do. I have misread the intent behind a que (source: automatic check at start, confidence 0.9)
- 2026-11-19 [mistake] Project pb2e6fac (make) failed: Команда /read URL: безопасно прочитать страницу по ссылке владельца. 
Только https, запретить localh (source: project engine, confidence 1.0)

## Code version
- version 4f23e029; identity probe: see the latest 'extension' entry above
- .github/workflows/agent.yml sha256 d97f2eda48c8740c
- CHARTER.md sha256 172ef887b5069d1c
- FACTS.md sha256 cbed9d66752b513d
- README.md sha256 c8d0e9f74257ddf7
- agent.py sha256 25d42ceb2825f62c
- docs/agent-card.json sha256 c4fdab641369c19c
- parts/part_01_core.py sha256 4fc9a336c5e423e7
- parts/part_02_memory.py sha256 97fbefc78859d3a7
- parts/part_03_adapters.py sha256 bb01335972e8352f
- parts/part_03a_bluesky.py sha256 b13a1f99e82e7d20
- parts/part_03b_moltbook.py sha256 b485533dd872afe2
- parts/part_03c_mastodon.py sha256 88edc2d7438d5c91
- parts/part_03h_vk.py sha256 d14bde13a3e63cce
- parts/part_03z_registry.py sha256 999a188bf2ef72b4
- parts/part_04_research.py sha256 351548e6e134a4b2
- parts/part_05_tools_sandbox.py sha256 0a3d3de9f02b4c26
- parts/part_06_owner_chat.py sha256 5fab7aed548643cb
- parts/part_06a_private_lab.py sha256 c4e8c1c91033283a
- parts/part_06b_selfmap.py sha256 a5e7913448442e4a
- parts/part_06c_bio.py sha256 4676c43dd0b7ed95
- parts/part_06d_backup_identity.py sha256 2c86d92358774114
- parts/part_06e_transparency.py sha256 04882b031b7ad001
- parts/part_06f_housekeeping.py sha256 bfc18b9b61ea07ef
- parts/part_06g_search.py sha256 d0808768b237f2aa
- parts/part_06h_config.py sha256 c23976061bcf7e24
- parts/part_06i_projects.py sha256 4c006e461731da2a
- parts/part_06j_health.py sha256 6bcb754598160f37
- parts/part_06k_content.py sha256 bf044056c023373f
- parts/part_06l_voice.py sha256 7b75564a7cbd6686
- parts/part_06m_resilience.py sha256 3ed55f37eb84853c
- parts/part_06n_platform_cmds.py sha256 cf55fc1e926d7618
- parts/part_06p_vk_page.py sha256 d9b76e5b30857ece
- parts/part_06q_tune.py sha256 47e7b079125e2ddc
- parts/part_06r_intuition.py sha256 2b96cfb6f1488bb5
- parts/part_06s_grounding.py sha256 c38074695c36ceae
- parts/part_06t_lookup.py sha256 e9769565850da63e
- parts/part_06u_search.py sha256 92da9c8379e6f4bf
- parts/part_06v_privacy.py sha256 09d036f4eb70e862
- parts/part_06w_tips.py sha256 1b4ff58b0d53afc0
- parts/part_06x_models.py sha256 504d15718796b90d
- parts/part_06z_own_loader.py sha256 ec35f80911a9dcb4
- parts/part_06zq_perplat.py sha256 29b5b32e0e6aa712
- parts/part_06zr_focus.py sha256 3833712c2684c407
- parts/part_06zs_safefetch.py sha256 501d1cdd448849d0
- parts/part_06zv_clean.py sha256 f5f6af00e80ce229
- parts/part_06zw_modelscout.py sha256 b00ff7422f8a6e09
- parts/part_06zx_scout.py sha256 ba8d0868050aca01
- parts/part_06zy_notes.py sha256 cc5360f755576ebc
- parts/part_06zz_make.py sha256 c4c49f02bef33ad9
- parts/part_06zzx_autorun.py sha256 b51a47089c64054c
- parts/part_06zzy_watchdog.py sha256 ccb91bfcdda75de9
- parts/part_07_main_loop.py sha256 07b3750715caef10

## Model use yesterday
- {"calls": {"gemini": 300, "groq": 216, "openrouter": 31, "groqq": 180}, "tokens": {"gemini": 504142, "groq": 115994, "openrouter": 13908, "groqq": 56901}}
