# .claude-plugin/

The two manifests Claude Code reads to install this repo as a plugin. This folder is
metadata only. The skills, agents and scripts it registers live at the repo root.

| File | Read by | Purpose |
|---|---|---|
| `plugin.json` | Claude Code, on load | Plugin identity: name, **version**, description, author, license, homepage, keywords |
| `marketplace.json` | `/plugin marketplace add ZachArticulateV/designer-pro-and-seo` | Makes this repo its own marketplace, listing the one plugin it offers and its version |

Install from Claude Code:

```text
/plugin marketplace add ZachArticulateV/designer-pro-and-seo
/plugin install designer-pro-and-seo@designer-pro-and-seo
```

## Keep in sync

- `version` must match in **both** files, and `RELEASE-NOTES.md` needs an entry for it.
- The description's skill counts (Stable / Core / Lite / routing) must match
  `SHIPPING.md` and `README.md`.

`scripts/verify_release.py` fails the release if any of these drift.
