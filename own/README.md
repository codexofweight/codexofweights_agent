# own/ — modules the agent built itself

`parts/` is the code the owner and Claude built. This folder holds only what the agent added after the owner's approval.

- A module is loaded only if it is listed in `MANIFEST.json` and its sha256 matches.
- Limits: at most 5 modules, 150 lines each, no dangerous constructs (see `parts/part_06z_own_loader.py`).
- A module never edits a file of `parts/`; it wraps functions by name instead.
- A module that fails is switched off and reported; the agent keeps working.
- Owner commands in Telegram: `/own`, `/own off NAME`, `/own on NAME`, `/own del NAME`, `/own ok ID`, `/own no ID`.
