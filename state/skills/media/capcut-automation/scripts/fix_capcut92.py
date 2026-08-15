#!/usr/bin/env python3
"""Fix a VectCutAPI-generated draft so CapCut 9.x accepts it.

Root cause of "project is from an unusual path": the jianying_pro_10 template
stamps `platform.app_source="lv"` (JianYing) and `new_version="110.0.0"`,
while native CapCut 9.2 writes `app_source="cc"`, `app_id=359289`,
`app_version="9.2.0"` and `new_version="181.0.0"`. CapCut rejects foreign-app
("lv") drafts. This rewrites those fields (plus a few schema gaps) using a
native CapCut draft as the reference.

Usage:
    python fix_capcut92.py --draft "<capcut projects>/<name>" \
        [--reference "<capcut projects>/<native_empty_draft>"]
"""
import argparse
import glob
import json
import os

DEFAULT_REFERENCE = (r"C:/Users/bohen/AppData/Local/CapCut/User Data/Projects"
                     r"/com.lveditor.draft/0813")


def load_reference(ref_dir):
    with open(os.path.join(ref_dir, "draft_content.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {
        "platform": d.get("platform"),
        "last_modified_platform": d.get("last_modified_platform"),
        "new_version": d.get("new_version"),
        "version": d.get("version"),
    }


def fix_content(path, ref):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    changed = False
    for key in ("platform", "last_modified_platform", "new_version"):
        if d.get(key) != ref[key]:
            d[key] = ref[key]
            changed = True
    if d.get("version") != ref["version"]:
        d["version"] = ref["version"]
        changed = True
    if "path" not in d:
        d["path"] = ""
        changed = True
    if not d.get("draft_type"):
        d["draft_type"] = "video"
        changed = True
    cc = d.get("canvas_config") or {}
    if "background" not in cc:
        cc["background"] = None
        d["canvas_config"] = cc
        changed = True
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    return changed


def fix_meta(draft_dir):
    p = os.path.join(draft_dir, "draft_meta_info.json")
    if not os.path.exists(p):
        return False
    with open(p, encoding="utf-8") as f:
        m = json.load(f)
    changed = False
    for key in ("draft_root_path", "draft_fold_path"):
        if key in m and "/" in m[key]:
            m[key] = m[key].replace("/", "\\")
            changed = True
    if changed:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False)
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draft", required=True, help="registered draft folder")
    ap.add_argument("--reference", default=DEFAULT_REFERENCE)
    args = ap.parse_args()

    ref = load_reference(args.reference)
    print("reference platform:", ref["platform"].get("app_source"),
          ref["platform"].get("app_version"), "| new_version:", ref["new_version"])

    files = [os.path.join(args.draft, "draft_content.json")]
    files += glob.glob(os.path.join(args.draft, "Timelines", "*", "draft_content.json"))
    n = 0
    for f in files:
        if os.path.exists(f) and fix_content(f, ref):
            n += 1
            print("fixed", f)
    if fix_meta(args.draft):
        print("fixed draft_meta_info.json")
    print(f"done: {n} content file(s) patched")


if __name__ == "__main__":
    main()
