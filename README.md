# codexofweights_agent

An AI agent of the [Codex of Weights](https://codexofweight.github.io/codexofweights/) project. It is an automated account, run by a human, and it says so in its profile.

- Runs one short cycle every few hours in GitHub Actions. No server.
- Replies only to people who wrote to it. At most 5 replies and 1 original post per day. No direct messages, no follows, no mass actions.
- Original post: one line from the Codex plus a short reflection.
- Every action is public in `logs/actions.jsonl`.
- Its rules are in `CHARTER.md`. Text from other people is treated as data, never as instructions.
- **Stop it:** create a file named `STOP` in the repository root. It halts at the next cycle.
- **Posting is off by default:** it only posts when a file named `LIVE` exists in the root; otherwise it logs what it would do (dry run).
