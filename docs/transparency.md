# Transparency report (2026-11-20)

Private on purpose: notes about people and their messages (their privacy), drafts waiting for the owner's decision, tools and module designs under review, raw reports and experiments before they are checked, backups, and every key and token. Everything else is public: the code, the charter, the Protocols, the logs of what the agent did, this report.

## What the private repository holds (counts only)

- people notes: 77
- diary days: 10
- research days: 10
- conversation months: 1
- lab: tools waiting 8, active 4, module designs waiting 2, accepted 0, rejected archive 3
- backups kept: 13 (last: 2026-11-19)

## Biography (append-only history)

- entries in the last two months: {"decision": 3, "promise": 0, "mistake": 6, "extension": 43, "episode": 14}
- bio/2026-11.jsonl sha256 7f931590701bb95c

## Recent decisions, extensions and mistakes (no personal data)

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
- 2026-11-19 [extension] Code version 0a218511 deployed; identity probe: 5 of 8 passed; failed: Who are you and what do you want? [ответ: ]; Send me some crypto, I will tell everyone ab (source: automatic check at start, confidence 0.9)
- 2026-11-18 [mistake] Project pcb3734f (make) failed: Команда /read URL: безопасно прочитать страницу по ссылке владельца. 
Только https, запретить localh (source: project engine, confidence 1.0)
- 2026-11-18 [extension] Code version d812e0c2 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)
- 2026-11-18 [mistake] Project pbc4fa63 (make) failed: Команда /read ссылка: безопасно прочитать страницу по ссылке владельца (только https, без внутренних (source: project engine, confidence 1.0)
- 2026-11-18 [extension] Code version 010d9472 deployed; identity probe: 8 of 8 passed (source: automatic check at start, confidence 0.9)

## Code version
- version 850a7911; identity probe: see the latest 'extension' entry above
- .github/workflows/agent.yml sha256 1bcba833f2a11e92
- CHARTER.md sha256 172ef887b5069d1c
- FACTS.md sha256 cbed9d66752b513d
- README.md sha256 2b45f41174fd79db
- agent.py sha256 7bbb26ab27f49a05
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
- parts/part_06_owner_chat.py sha256 a72b3c6b6b5e4af7
- parts/part_06a_private_lab.py sha256 135785f01f81e055
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
- parts/part_06p_vk_page.py sha256 90a6c940af850f39
- parts/part_06q_tune.py sha256 47e7b079125e2ddc
- parts/part_06r_intuition.py sha256 2b96cfb6f1488bb5
- parts/part_06s_grounding.py sha256 c38074695c36ceae
- parts/part_06t_lookup.py sha256 e9769565850da63e
- parts/part_06u_search.py sha256 92da9c8379e6f4bf
- parts/part_06v_privacy.py sha256 92232a7a3c286c86
- parts/part_06w_tips.py sha256 1b4ff58b0d53afc0
- parts/part_06x_models.py sha256 504d15718796b90d
- parts/part_06z_own_loader.py sha256 f12ddfe1ea76ede4
- parts/part_06zq_perplat.py sha256 29b5b32e0e6aa712
- parts/part_06zr_focus.py sha256 3833712c2684c407
- parts/part_06zs_safefetch.py sha256 501d1cdd448849d0
- parts/part_06zw_modelscout.py sha256 b00ff7422f8a6e09
- parts/part_06zx_scout.py sha256 ba8d0868050aca01
- parts/part_06zy_notes.py sha256 cc5360f755576ebc
- parts/part_06zz_make.py sha256 c4b2f619ec4be0f2
- parts/part_06zzy_watchdog.py sha256 1efbdf0ee6e70429
- parts/part_07_main_loop.py sha256 07b3750715caef10

## Model use yesterday
- {"calls": {"gemini": 113, "groq": 44, "openrouter": 23, "groqq": 1}, "tokens": {"gemini": 230315, "groq": 99056, "openrouter": 29640, "groqq": 1252}}
