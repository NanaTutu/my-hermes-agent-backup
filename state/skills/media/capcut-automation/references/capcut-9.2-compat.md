# CapCut 9.2 compatibility — "unusual path" rejection + fix

## Symptom
Opening a registered VectCutAPI draft in CapCut 9.2.0.3931 shows:
  "project is from an unusual path and cannot be used currently"
CapCut does NOT modify the draft on this failure (no rewrite, no
`tm_draft_removed` in `root_meta_info.json`). It hits EVERY draft produced by
the `jianying_pro_10` template, not one specific draft.

## Root cause
`jianying_pro_10` is the only VectCutAPI profile that emits the modern
`draft_content.json` format, but it stamps JianYing ("lv") app metadata.
CapCut 9.2 sees a draft authored by a foreign app and refuses it.

| field | native CapCut 9.2 (`cc`) | VectCutAPI `jianying_pro_10` (`lv`) |
|---|---|---|
| `platform.app_source` | `"cc"` | `"lv"` |
| `platform.app_id` | `359289` | `3704` |
| `platform.app_version` | `"9.2.0"` | `"10.2.0"` |
| `platform.device_id` / `hard_disk_id` / `mac_address` / `os_version` | present | absent |
| `new_version` | `"181.0.0"` | `"110.0.0"` |
| top-level `path` | `""` | missing |
| top-level `draft_type` | `"video"` | missing |
| `canvas_config.background` | `null` | missing |
| `version` | `360000` | `360000` (same) |

`config.json`'s `"is_capcut_env": true` does NOT help: `settings/local.py` uses
it to toggle the MATERIAL export format (cc vs lv field names), but the
`platform` dict comes from `profile.platform` (still `JIANYING_10_PLATFORM`).
Result: materials exported cc-style while the platform block still says `lv` —
the inconsistency is what CapCut rejects.

## Fix
`scripts/fix_capcut92.py --draft "<capcut projects>/<name>"` reads a native
CapCut draft (default reference `.../com.lveditor.draft/0813`) and patches the
target's `draft_content.json` + `Timelines/*/draft_content.json`:
  - `platform` + `last_modified_platform` → the native `cc` block (copies this
    machine's real device/hard-disk/mac ids),
  - `new_version` → `"181.0.0"`,
  - adds `path: ""`, `draft_type: "video"`, `canvas_config.background: null`.
It also rewrites `draft_meta_info.json` `draft_root_path`/`draft_fold_path`
with backslashes (native style).

Run it AFTER `register_draft.py`, then have the user fully quit CapCut and
reopen (CapCut caches the draft list). The user must quit, not minimize.

## Diagnostic trail
- Confirm a draft's platform: `draft_content.json["platform"]["app_source"]`
  — `"lv"` = will be rejected, `"cc"` = correct.
- To isolate a draft-specific vs systemic rejection: compare against a native
  empty draft (create one in CapCut, or reuse an existing native project
  folder). If native says `"cc"` and the generated one says `"lv"`, it's the
  template, not your media.
- Native draft folders have `draft_cover.jpg`; generated ones don't — cosmetic,
  not the blocker.

## Next escalation (if still rejected after the fix)
The remaining difference is the material OBJECT schema (pyJianYingDraft's
export vs native CapCut). Next step then: full transplant — use a native CapCut
draft's `draft_content.json` as the skeleton and move `materials` + `tracks`
(+ the `assets/` folder) into it, then re-apply the path fixes.
