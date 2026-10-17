"""Isolated installer/restore/MCP proof; no real CapCut writes or Claude registration."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(part)
    return value.hexdigest()


def json_inventory(root):
    root = Path(root)
    if not root.is_dir():
        return {}
    return {p.relative_to(root).as_posix(): digest(p) for p in root.rglob("*.json") if p.is_file()}


def ensure(ok, message):
    if not ok:
        raise AssertionError(message)


def main():
    base = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=base / "outputs/CapCut-SFX-Learning-Claude-Code-FULL-2026-10-13-v0.1.15")
    parser.add_argument("--test-root", type=Path)
    parser.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    test_root = (args.test_root or base / "outputs" / ("claude-migration-validation-" + str(time.time_ns()))).resolve()
    ensure(test_root.is_relative_to(base / "outputs"), "Test root must be inside the workspace outputs directory.")
    ensure(not test_root.exists(), "Preserve previous validation results; choose a fresh test root.")
    test_root.mkdir(parents=True)
    state, drafts = test_root / "state", test_root / "test-drafts"
    drafts.mkdir()
    info = read(bundle / "BUNDLE_INFO.json")
    asset_map = {key.replace("\\", "/").casefold(): str(bundle / relative) for key, relative in info["asset_map"].items()}
    prefixes = ((info["old_state_root"], str(state)), (info["old_model_root"], str(bundle / "models")),
                (info["old_library_root"], str(bundle / "library")))

    def expected_rebase(value):
        if isinstance(value, dict):
            return {key: expected_rebase(item) for key, item in value.items()}
        if isinstance(value, list):
            return [expected_rebase(item) for item in value]
        if not isinstance(value, str):
            return value
        normalized = value.replace("\\", "/")
        key = normalized.casefold()
        if key in asset_map:
            return asset_map[key]
        for old, new in prefixes:
            old = old.replace("\\", "/")
            if key == old.casefold() or key.startswith(old.casefold() + "/"):
                return new + normalized[len(old):]
        return value

    native_root = Path(info["old_draft_root"])
    native_before = json_inventory(native_root)
    live_state = Path(info["old_state_root"])
    live_before = {relative: digest(live_state / relative) for relative in
                   ("memory.json", "data/zoom_style.json", "data/hook_style.json", "config.json", "runtime.json")
                   if (live_state / relative).is_file()}
    # A native project-shaped guard proves read-only discovery preserves draft bytes.
    fixture = drafts / "migration-guard" / "Timelines" / "GUARD"
    fixture.mkdir(parents=True)
    write(fixture / "draft_content.json", {"id": "GUARD", "duration": 1_000_000,
                                          "materials": {"videos": [], "audios": [], "texts": []}, "tracks": []})
    write(fixture.parent / "project.json", {"timelines": [{"id": "GUARD", "name": "migration-guard"}]})
    guards = json_inventory(drafts)
    python = bundle / "runtime/env/Scripts/python.exe"
    environment = dict(os.environ)
    environment.update(SOUNDPILOT_STATE=str(state), PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1",
                       CT2_FORCE_CPU_ISA="GENERIC", CT2_USE_MKL="0", HF_HUB_OFFLINE="1",
                       TRANSFORMERS_OFFLINE="1")
    system = Path(os.environ.get("SystemRoot", "C:/Windows"))
    environment["PATH"] = os.pathsep.join(map(str, (bundle / "runtime/tools", system / "System32",
                                                          system / "System32/WindowsPowerShell/v1.0")))

    def run(command, timeout=240):
        process = subprocess.run(list(map(str, command)), env=environment, capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", timeout=timeout)
        ensure(process.returncode == 0, f"Command failed ({process.returncode}): {(process.stderr or process.stdout)[-7000:]}")
        return process.stdout

    print("Installing the portable bundle into isolated workspace state; Claude registration disabled.", flush=True)
    install = run([system / "System32/WindowsPowerShell/v1.0/powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                   "-File", bundle / "INSTALL_CLAUDE_CODE.ps1", "-StateRoot", state, "-DraftRoot", drafts,
                   "-UsePortable", "-NoRegister"])
    (test_root / "INSTALL_OUTPUT.txt").write_text(install, encoding="utf-8")
    archive = read(bundle / "state/memory.json")
    restored = read(state / "memory.json")
    ensure(restored["profile"]["version"] == info["sfx_style_version"], "SFX version was not restored.")
    ensure(len(restored["examples"]) == info["sfx_examples"], "SFX examples were not restored.")
    ensure(len(restored.get("receipts", [])) == len(archive.get("receipts", [])), "SFX revision receipts were lost.")
    ensure(restored == expected_rebase(archive), "SFX profile/examples/receipts content changed beyond path rebasing.")
    zoom, hook = read(state / "data/zoom_style.json"), read(state / "data/hook_style.json")
    ensure(zoom == expected_rebase(read(bundle / "state/data/zoom_style.json")), "Zoom reference content changed beyond path rebasing.")
    ensure(hook == expected_rebase(read(bundle / "state/data/hook_style.json")), "Hook reference content changed beyond path rebasing.")
    ensure(zoom["version"] == info["zoom_style_version"] and len(zoom["references"]) == info["zoom_reference_timelines"], "Zoom memory differs.")
    ensure(sum(len(r.get("events", [])) for r in zoom["references"]) == info["zoom_reference_events"], "Zoom event count differs.")
    ensure(hook["version"] == info["hook_style_version"] and len(hook.get("references", [])) == info["hook_references"], "Hook memory differs.")
    report = read(state / "migration-restore-report.json")
    ensure(all(report[name + "_restored"] for name in ("sfx", "zoom", "hook")), "Fresh restore did not select all archive components.")
    cache_files = sum(1 for p in state.rglob("*") if p.is_file())
    print("Checking newer SFX, zoom and hook memories independently, then older-memory upgrades.", flush=True)
    future, future_zoom, future_hook = copy.deepcopy(restored), copy.deepcopy(zoom), copy.deepcopy(hook)
    future["profile"]["version"] += 1
    future["profile"]["migration_test_sentinel"] = "keep-newer-sfx"
    future_zoom["version"] += 1
    future_zoom["migration_test_sentinel"] = "keep-newer-zoom"
    future_hook["version"] += 1
    future_hook["migration_test_sentinel"] = "keep-newer-hook"
    write(state / "memory.json", future)
    write(state / "data/zoom_style.json", future_zoom)
    write(state / "data/hook_style.json", future_hook)
    restore_command = [python, "-B", bundle / "migration/restore_state.py", "--state", state, "--draft-root", drafts]
    newer_report = json.loads(run(restore_command))
    ensure(all(not newer_report[name + "_restored"] for name in ("sfx", "zoom", "hook")), "A newer component was overwritten.")
    ensure(read(state / "memory.json")["profile"]["migration_test_sentinel"] == "keep-newer-sfx", "Newer SFX marker lost.")
    ensure(read(state / "data/zoom_style.json")["migration_test_sentinel"] == "keep-newer-zoom", "Newer zoom marker lost.")
    ensure(read(state / "data/hook_style.json")["migration_test_sentinel"] == "keep-newer-hook", "Newer hook marker lost.")
    ensure(read(state / "memory.json") == future, "Newer SFX content was modified.")
    ensure(read(state / "data/zoom_style.json") == future_zoom, "Newer zoom content was modified.")
    ensure(read(state / "data/hook_style.json") == future_hook, "Newer hook content was modified.")
    for relative, value, nested in (("memory.json", restored, True), ("data/zoom_style.json", zoom, False), ("data/hook_style.json", hook, False)):
        older = copy.deepcopy(value)
        (older["profile"] if nested else older)["version"] = -1
        write(state / relative, older)
    older_report = json.loads(run(restore_command))
    ensure(all(older_report[name + "_restored"] for name in ("sfx", "zoom", "hook")), "An older component was not upgraded.")
    before_health = json_inventory(state)
    print("Verifying exact portable dependencies, offline model, and actual 31-tool MCP stdio discovery.", flush=True)
    health_command = [python, "-B", bundle / "migration/health_check.py", "--state", state, "--mcp"]
    if args.verify_files:
        health_command.append("--verify-files")
    health = json.loads(run(health_command, timeout=300))
    ensure(health["ok"] and health["runtime"]["portable_runtime_rebased"], "Health runtime verification failed.")
    ensure(health["mcp"]["tool_count"] == info["mcp_tools_expected"] == 31, "MCP tool count differs.")
    schemas = health["mcp"].pop("tool_schemas")
    write(bundle / "MCP_TOOL_SCHEMAS.json", {"transport": "stdio", "actual_tool_count": len(schemas), "schemas": schemas})
    ensure(before_health == json_inventory(state), "Health check changed selected state JSON.")
    # Exercise the default same-PC reuse branch against isolated state using the
    # real installed runtime shape (which may deliberately omit ffmpeg_bin).
    shared_reuse = False
    original_runtime_path = live_state / "runtime.json"
    portable_runtime = read(state / "runtime.json")
    if original_runtime_path.is_file() and Path(read(original_runtime_path)["python"]).is_file():
        print("Checking same-PC runtime reuse without changing existing learned state.", flush=True)
        write(state / "runtime.json", read(original_runtime_path))
        before_reuse = json_inventory(state)
        reuse_output = run([system / "System32/WindowsPowerShell/v1.0/powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", bundle / "INSTALL_CLAUDE_CODE.ps1", "-StateRoot", state, "-DraftRoot", drafts, "-NoRegister"])
        (test_root / "SAME_PC_REUSE_OUTPUT.txt").write_text(reuse_output, encoding="utf-8")
        session = read(bundle / "local-install/claude-session.json")
        ensure(session["shared_existing_runtime"] is True, "Default same-PC installation did not reuse current runtime/state.")
        ensure(before_reuse == json_inventory(state), "Same-PC reuse changed selected learned state JSON.")
        shared_reuse = True
        write(state / "runtime.json", portable_runtime)
    ensure(guards == json_inventory(drafts), "A native fixture draft was changed.")
    ensure(native_before == json_inventory(native_root), "Live CapCut project metadata changed during validation.")
    ensure(live_before == {relative: digest(live_state / relative) for relative in live_before}, "Live learned state changed during validation.")
    result = {"passed": True, "ok": True, "snapshot_date": info["snapshot_date"], "plugin_version": info["plugin_version"],
              "test_root": str(test_root), "fresh_restore": report, "newer_components_preserved": True,
              "older_components_upgraded": True, "history_cache_files_present": cache_files,
              "same_pc_runtime_reuse_preserves_state": shared_reuse,
              "actual_mcp_31_tools_verified": True, "native_fixture_json_unchanged": True,
              "live_capcut_json_files_unchanged": len(native_before), "live_learned_state_unchanged": True,
              "host_registration_in_test": False, "creative_cross_host_equivalence_measured": False, "health": health}
    write(test_root / "VALIDATION_RESULTS.json", result)
    write(bundle / "TRANSFER_TEST_RESULTS.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
