# Coding benchmark of the free models (2026-11-17)

| model | provider | passed tests | where it failed |
|---|---|---|---|
| gemini-3.1-flash-lite | gemini | 51/51 (100%) | - |
| openai/gpt-oss-120b | groq | 51/51 (100%) | - |
| qwen/qwen3.8-27b | groq | 51/51 (100%) | - |
| codestral-latest | mistral | 49/51 (96%) | dedupe 6/8 |
| codestral-2508 | mistral | 48/51 (94%) | dedupe 6/8; filename 9/10 |
| nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | openrouter | 41/51 (80%) | filename 0/10 |
| openai/gpt-oss-20b | groq | 30/51 (59%) | duration 0/11; filename 0/10 |
| nvidia/nemotron-3.5-super-vl:free | openrouter | 30/51 (59%) | duration 0/11; filename 0/10 |
| nvidia/nemotron-3-ultra-550b-a55b:free | openrouter | 23/41 (56%) | duration 0/1; filename 0/10; bugfix 0/7 |
| nvidia/nemotron-3.5-lightning:free | openrouter | 15/51 (29%) | duration 0/11; dedupe 0/8; lru 0/7; filename 0/10 |
| gemini-2.5-flash | gemini | 0/65 (0%) | duration:HTTP 404; dedupe:HTTP 404; lru:HTTP 404; intervals:HTTP 404; filename:HTTP 404; bugfix:HTTP 404 |
| gemini-2.5-pro | gemini | 0/65 (0%) | duration:HTTP 404; dedupe:HTTP 404; lru:HTTP 404; intervals:HTTP 404; filename:HTTP 404; bugfix:HTTP 404 |
| gemini-2.5-flash-lite | gemini | 0/65 (0%) | duration:HTTP 404; dedupe:HTTP 404; lru:HTTP 404; intervals:HTTP 404; filename:HTTP 404; bugfix:HTTP 404 |
| mistral-large-latest | mistral | 0/65 (0%) | duration:HTTP 403; dedupe:HTTP 403; lru:HTTP 403; intervals:HTTP 403; filename:HTTP 403; bugfix:HTTP 403 |
| mistral-medium-latest | mistral | 0/65 (0%) | duration:HTTP 429; dedupe:HTTP 429; lru:HTTP 429; intervals:HTTP 429; filename:HTTP 429; bugfix:HTTP 429 |
