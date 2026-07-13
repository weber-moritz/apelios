Modify the fixture layer runtime manager to load and merge all JSON files from the patch directory, similar to how the router layer works.

Currently, the fixture runtime manager only loads `default.json`. This prevents users from splitting fixtures into separate files.

The fixture layer should:
1. Load `default.json` first (as the base)
2. Load all other `*.json` files from the patch directory
3. Merge all fixtures from all files into a single patch configuration

This allows users to:
- Have separate fixture files for different lighting setups
- Enable/disable fixtures by renaming files (e.g., `my-fixture.json` → `my-fixture.json-inactive`)
- Organize fixtures more cleanly
