#!/usr/bin/env python3
"""Register a VectCutAPI-generated draft into CapCut's project list.

Copies output/<draft_id> into the CapCut projects dir under a human name,
fixes video material duration (only when 0) and asset paths, and upserts the
root_meta_info.json index entry so CapCut shows it on the Home screen.

Usage (from the VectCutAPI dir, its venv):
    .venv/Scripts/python.exe register_draft.py --src output/<draft_id> --name my_video
"""
import argparse
import glob
import json
import os
import shutil
import sys
import time
import uuid

DEFAULT_PROJECTS = r"C:/Users/bohen/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft"


def fix_materials(d, dst, dur_us):
    """Rewrite media material paths into the draft's assets/ dir and stamp zero
    durations. Photos (still images) live in assets/image/, real videos in
    assets/video/, audio in assets/audio/ (audio stores its filename under
    `name`, not `material_name`). Returns True if anything changed."""
    changed = False
    for v in d.get("materials", {}).get("videos", []):
        if v.get("duration") == 0 and dur_us:
            v["duration"] = dur_us
            changed = True
        mn = v.get("material_name") or v.get("name") or ""
        subdir = "image" if v.get("type") == "photo" else "video"
        newpath = os.path.join(dst, "assets", subdir, mn).replace("\\", "/")
        if mn and v.get("path") != newpath:
            v["path"] = newpath
            v["media_path"] = newpath
            changed = True
    for a in d.get("materials", {}).get("audios", []):
        if a.get("duration") == 0 and dur_us:
            a["duration"] = dur_us
            changed = True
        mn = a.get("material_name") or a.get("name") or ""
        newpath = os.path.join(dst, "assets", "audio", mn).replace("\\", "/")
        if mn and a.get("path") != newpath:
            a["path"] = newpath
            changed = True
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, help="source draft folder (e.g. output/<draft_id>)")
    ap.add_argument("--name", required=True, help="draft name shown in CapCut")
    ap.add_argument("--duration", type=float, default=3.0,
                    help="seconds to stamp on video materials whose duration is 0 (CapCut re-derives anyway)")
    ap.add_argument("--projects", default=DEFAULT_PROJECTS, help="CapCut projects dir")
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    root = args.projects
    dst = os.path.join(root, args.name)
    dur_us = int(args.duration * 1_000_000)

    if not os.path.exists(src):
        sys.exit(f"ERROR: source draft not found: {src}")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print("copied ->", dst)

    # content files CapCut reads (root + timeline mirrors)
    content_files = [
        os.path.join(dst, "draft_content.json"),
        os.path.join(dst, "draft_content.json.bak"),
        os.path.join(dst, "template-2.tmp"),
    ]
    content_files += glob.glob(os.path.join(dst, "Timelines", "*", "draft_content.json"))
    content_files += glob.glob(os.path.join(dst, "Timelines", "*", "draft_content.json.bak"))
    content_files += glob.glob(os.path.join(dst, "Timelines", "*", "template-2.tmp"))
    content_files += glob.glob(os.path.join(dst, "Timelines", "*", "template.tmp"))

    fixed = 0
    for f in content_files:
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        if fix_materials(d, dst, dur_us):
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False)
            fixed += 1
    print(f"fixed {fixed} content files (duration<={dur_us}us, path -> inside draft)")

    meta_path = os.path.join(root, "root_meta_info.json")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
    else:
        meta = {"all_draft_store": [], "draft_ids": 0, "root_path": root.replace("\\", "\\")}

    now_us = int(time.time() * 1_000_000)
    entry = {
        "cloud_draft_cover": False, "cloud_draft_sync": False,
        "draft_cloud_last_action_download": False, "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "", "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "", "draft_cover": "",
        "draft_fold_path": dst.replace("/", "\\"),
        "draft_id": str(uuid.uuid4()).upper(),
        "draft_is_ai_shorts": False, "draft_is_cloud_temp_draft": False,
        "draft_is_invisible": False, "draft_is_pippit_draft": False,
        "draft_is_web_article_video": False,
        "draft_json_file": os.path.join(dst, "draft_content.json").replace("/", "\\"),
        "draft_name": args.name,
        "draft_new_version": "", "draft_root_path": root.replace("/", "\\"),
        "draft_timeline_materials_size": 0,
        "draft_type": "", "draft_web_article_video_enter_from": "",
        "pippit_avatar_url": "", "pippit_extra_info": "", "pippit_id": "",
        "pippit_user_name": "", "streaming_edit_draft_ready": True,
        "tm_draft_cloud_completed": "", "tm_draft_cloud_entry_id": -1,
        "tm_draft_cloud_modified": 0, "tm_draft_cloud_parent_entry_id": -1,
        "tm_draft_cloud_space_id": -1, "tm_draft_cloud_user_id": -1,
        "tm_draft_create": now_us, "tm_draft_modified": now_us,
        "tm_draft_removed": 0, "tm_duration": dur_us,
    }
    meta["all_draft_store"] = [e for e in meta["all_draft_store"] if e.get("draft_name") != args.name]
    meta["all_draft_store"].append(entry)
    meta["draft_ids"] = len(meta["all_draft_store"])
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False)
    print(f"registered '{args.name}' in root_meta_info.json; total drafts: {meta['draft_ids']}")


if __name__ == "__main__":
    main()
