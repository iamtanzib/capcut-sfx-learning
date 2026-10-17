"""Verify migration files/runtime/memory without changing the selected state or drafts.

MCP startup initializes its state, so --mcp uses a temporary minimal state clone.
Only initialize, list_tools and the read-only list_projects tool are exercised.
"""
from __future__ import annotations

import argparse
import collections
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/capcut-sfx-learning"
TOOLS = {
    "list_projects", "prepare_batch", "batch_status", "get_brief", "get_batch_briefs",
    "get_context", "get_context_batch", "exact_frame", "stage_plan", "audit_mix",
    "preflight_batch", "apply_batch", "learn_revision", "get_style_memory",
    "learn_zoom_style", "prepare_zoom_batch", "get_zoom_briefs", "get_zoom_context",
    "stage_zoom_plan", "preview_zoom_plan", "apply_zoom_batch", "learn_zoom_revision",
    "prepare_edit_batch", "get_edit_briefs", "apply_edit_batch", "learn_hook_style",
    "stage_hook_plan", "preview_hook_plan", "learn_hook_revision", "analysis_cache_status",
    "learn_edit_revision",
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require(ok: bool, message: str):
    if not ok:
        raise ValueError(message)


def sha(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def verify_manifest(path: Path):
    manifest = read(path)
    require(isinstance(manifest, dict), "SHA256 manifest must map relative paths to digests.")
    count = 0
    for relative, expected in manifest.items():
        target = (ROOT / relative).resolve()
        require(target.is_relative_to(ROOT), f"Manifest path escapes bundle: {relative}")
        # This is the only distributed file that installation intentionally rebases.
        if relative.replace("\\", "/") == "runtime/env/pyvenv.cfg":
            continue
        require(target.is_file(), f"Missing file: {relative}")
        require(sha(target) == expected, f"SHA256 mismatch: {relative}")
        count += 1
    return count


def package_pins():
    result = {}
    for line in (ROOT / "RUNTIME_PACKAGES.txt").read_text(encoding="utf-8-sig").splitlines():
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+)", line.strip())
        if match:
            result[match[1]] = match[2]
        elif line.strip() and not line.lstrip().startswith("#"):
            raise ValueError(f"Unrecognized exact package pin: {line}")
    require(bool(result), "Runtime package manifest is empty.")
    return result


def runtime_environment(state: Path, runtime: dict):
    environment = dict(os.environ)
    environment.update(SOUNDPILOT_STATE=str(state), PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1",
                       CT2_FORCE_CPU_ISA="GENERIC", CT2_USE_MKL="0", HF_HUB_OFFLINE="1",
                       TRANSFORMERS_OFFLINE="1")
    environment["PATH"] = str(runtime["ffmpeg_bin"]) + os.pathsep + environment.get("PATH", "")
    return environment


def probe_runtime(state: Path, cfg: dict, runtime: dict):
    python = Path(runtime["python"]).resolve()
    require(python.is_file(), f"Configured runtime missing: {python}")
    pins = package_pins()
    payload = {"pins": pins, "model_root": cfg["model_root"],
               "model": cfg.get("speech_model", "base.en"), "threads": cfg.get("speech_threads", 2)}
    code = r'''
import importlib.metadata as metadata, json, sys
from pathlib import Path
p = json.loads(sys.argv[1])
versions = {name: metadata.version(name) for name in p['pins']}
mismatches = {name: {'expected': version, 'actual': versions[name]} for name, version in p['pins'].items() if versions[name] != version}
if mismatches: raise RuntimeError('Package versions differ: '+json.dumps(mismatches))
import numpy, mcp, cv2, tiktoken, onnxruntime, fastembed, av, PIL
from faster_whisper import WhisperModel
model = WhisperModel(p['model'], device='cpu', compute_type='int8', cpu_threads=p['threads'], num_workers=1, download_root=str(Path(p['model_root'])/'speech'), local_files_only=True)
segments, details = model.transcribe(numpy.zeros(16000, dtype=numpy.float32), language='en', beam_size=1, vad_filter=False, word_timestamps=True, condition_on_previous_text=False)
rows = list(segments)  # Consume the generator to prove local encoder/decoder inference runs.
print(json.dumps({'python': sys.executable, 'prefix': sys.prefix, 'base_prefix': sys.base_prefix, 'python_version': sys.version.split()[0], 'exact_packages_verified': len(versions), 'dependency_versions': versions, 'offline_speech_model': p['model'], 'offline_speech_inference': True, 'silent_probe_segments': len(rows), 'speech_device': 'cpu', 'speech_compute_type': 'int8'}))
'''
    result = subprocess.run([str(python), "-B", "-c", code, json.dumps(payload)],
                            env=runtime_environment(state, runtime), capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=120)
    require(result.returncode == 0, f"Runtime/model probe failed: {(result.stderr or result.stdout)[-6000:]}")
    report = json.loads(result.stdout)
    # For shared installations the active interpreter can intentionally be outside this ZIP.
    portable = python == (ROOT / "runtime/env/Scripts/python.exe").resolve()
    if portable:
        require(Path(report["prefix"]).resolve() == (ROOT / "runtime/env").resolve(), "Portable venv prefix is wrong.")
        require(Path(report["base_prefix"]).resolve() == (ROOT / "runtime/python").resolve(), "Portable Python home was not rebased. Rerun installation.")
        home = dict(line.split(" = ", 1) for line in (ROOT / "runtime/env/pyvenv.cfg").read_text(encoding="utf-8-sig").splitlines() if " = " in line)
        require(Path(home["home"]).resolve() == (ROOT / "runtime/python").resolve(), "pyvenv.cfg home is stale.")
        require(Path(home["executable"]).resolve() == (ROOT / "runtime/python/python.exe").resolve(), "pyvenv.cfg executable is stale.")
        require(home.get("include-system-site-packages", "").casefold() == "false", "Portable venv includes external packages.")
    report["portable_runtime_rebased"] = portable
    for name in ("ffmpeg", "ffprobe"):
        path = Path(runtime["ffmpeg_bin"]) / (name + (".exe" if os.name == "nt" else ""))
        require(path.is_file(), f"Configured {name} missing: {path}")
        process = subprocess.run([str(path), "-version"], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=20)
        require(process.returncode == 0, f"{name} failed to start.")
        report[name] = {"path": str(path), "version": process.stdout.splitlines()[0]}
    return report


@contextmanager
def mcp_scratch():
    scratch = (ROOT / "local-install").resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    clone = scratch / ("capcut-mcp-health-" + uuid.uuid4().hex)
    # Python's secure tempfile mode 0700 can create a Windows ACL that excludes
    # restricted child-process tokens. Normal mkdir inherits the bundle ACL.
    clone.mkdir()
    try:
        yield clone
    finally:
        resolved = clone.resolve()
        require(resolved.parent == scratch and resolved.is_relative_to(ROOT), "Scratch cleanup escaped bundle.")
        shutil.rmtree(resolved)


def probe_mcp(state: Path, cfg: dict, runtime: dict):
    # Keep temporary writes inside the bundle, outside the selected learned state.
    with mcp_scratch() as clone:
        # The service's import-time recovery must run only against this clone.
        for relative in ("config.json", "runtime.json", "memory.json", "data/style_profile.json",
                         "data/examples.json", "data/zoom_style.json", "data/hook_style.json"):
            source = state / relative
            if source.is_file():
                target = clone / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        environment = runtime_environment(clone, runtime)
        powershell = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe")
        # Anonymous pipes also work on restricted Windows hosts where the SDK's
        # asyncio named-pipe client is denied. These are standard MCP JSON-RPC
        # messages against the actual launcher/server, not mocked tool results.
        process = subprocess.Popen([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PLUGIN / "launch.ps1")],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=environment, text=True, encoding="utf-8", errors="replace", bufsize=1,
                                   creationflags=0x08000000 if os.name == "nt" else 0)
        responses = queue.Queue()
        stderr = collections.deque(maxlen=100)

        def read_stdout():
            for line in process.stdout:
                try:
                    responses.put(json.loads(line))
                except ValueError:
                    responses.put({"invalid_stdout": line})
            responses.put({"eof": True})

        def read_stderr():
            for line in process.stderr:
                stderr.append(line.rstrip())

        threading.Thread(target=read_stdout, daemon=True).start()
        threading.Thread(target=read_stderr, daemon=True).start()
        deadline = time.monotonic() + 90

        def send(value):
            process.stdin.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
            process.stdin.flush()

        def rpc(identifier, method, params):
            send({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params})
            while True:
                try:
                    response = responses.get(timeout=max(0.001, deadline - time.monotonic()))
                except queue.Empty:
                    raise TimeoutError("MCP response timed out: " + "\n".join(stderr))
                require("invalid_stdout" not in response, f"Protocol stdout was polluted: {response}")
                require(not response.get("eof"), "MCP exited before replying: " + "\n".join(stderr))
                if response.get("id") == identifier:
                    require("error" not in response, f"MCP {method} error: {response.get('error')}")
                    return response["result"]

        try:
            startup = rpc(1, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                             "clientInfo": {"name": "capcut-migration-health", "version": "1.0"}})
            require("$defaults" in startup.get("instructions", ""), "MCP inherited-table instructions absent.")
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            listing = rpc(2, "tools/list", {})
            names = [tool["name"] for tool in listing["tools"]]
            require(len(names) == 31 and set(names) == TOOLS, f"MCP tools differ from v0.1.15: {names}")
            schema = {tool["name"]: tool["inputSchema"] for tool in listing["tools"]}
            require(schema["prepare_edit_batch"]["properties"]["mode"]["default"] == "full_combo", "Default full combo changed.")
            require(schema["prepare_batch"]["properties"]["include_zoom"]["default"] is True, "Default SFX+zoom changed.")
            for name in ("apply_batch", "apply_zoom_batch", "apply_edit_batch"):
                require(schema[name]["properties"]["auto_close"]["default"] is True, f"{name} auto_close changed.")
            require({"zooms", "hook_plan"}.issubset(schema["stage_plan"]["properties"]), "Full combo schema incomplete.")
            projects = rpc(3, "tools/call", {"name": "list_projects", "arguments": {}})
            require(not projects.get("isError"), "Read-only MCP list_projects failed.")
            return {"transport": "stdio", "protocol_version": startup["protocolVersion"],
                    "server_info": startup["serverInfo"], "tool_count": len(names), "tools": sorted(names),
                    "tool_schemas": schema, "list_projects_ok": True, "draft_root": cfg["draft_root"],
                    "state_clone_used": True, "capcut_project_writes": False}
        finally:
            process.stdin.close()  # EOF normally makes the MCP server exit cleanly.
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            process.stdout.close()
            process.stderr.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--verify-files", nargs="?", const=str(ROOT / "SHA256_FILES.json"), type=Path)
    parser.add_argument("--mcp", action="store_true")
    args = parser.parse_args()
    state = args.state.resolve()
    info = read(ROOT / "BUNDLE_INFO.json")
    cfg, runtime, memory = (read(state / relative) for relative in ("config.json", "runtime.json", "memory.json"))
    # Original same-PC Codex runtime.json may only contain the interpreter path.
    # Use bundled FFmpeg for checking without changing that existing file.
    runtime = {**runtime, "ffmpeg_bin": runtime.get("ffmpeg_bin") or str(ROOT / "runtime/tools")}
    for name in ("draft_root", "library", "model_root"):
        require(Path(cfg[name]).is_dir(), f"Configured {name} missing: {cfg[name]}")
    profile, examples = memory["profile"], memory["examples"]
    require(read(state / "data/style_profile.json") == profile, "Derived SFX profile differs from committed memory.")
    require(read(state / "data/examples.json") == examples, "Derived SFX examples differ from committed memory.")
    zoom, hook = (read(state / relative) for relative in ("data/zoom_style.json", "data/hook_style.json"))
    for active, expected, label in ((profile["version"], info["sfx_style_version"], "SFX"),
                                    (zoom["version"], info["zoom_style_version"], "zoom"),
                                    (hook["version"], info["hook_style_version"], "hook")):
        require(active >= expected, f"{label} memory is older than the bundle snapshot.")
    zoom_events = sum(len(reference.get("events", [])) for reference in zoom.get("references", []))
    counts = {"sfx_examples": len(examples), "zoom_reference_timelines": len(zoom.get("references", [])),
              "zoom_reference_events": zoom_events, "hook_references": len(hook.get("references", []))}
    for key, component, snapshot in (("sfx_examples", profile, "sfx_style_version"),
                                     ("zoom_reference_timelines", zoom, "zoom_style_version"),
                                     ("zoom_reference_events", zoom, "zoom_style_version"),
                                     ("hook_references", hook, "hook_style_version")):
        if component["version"] == info[snapshot]:
            require(counts[key] == info[key], f"Snapshot {key} differs: {counts[key]} != {info[key]}")
    catalog = read(state / "data/sound_catalog.json")
    require(bool(catalog), "SFX catalog is empty. Run installation/configure.")
    require(len({sound["name"].casefold() for sound in catalog}) == len(catalog), "Duplicate catalog filenames.")
    for sound in catalog:
        require(Path(sound["path"]).is_file(), f"Catalog sound missing: {sound['path']}")
    require(len(list(Path(cfg["model_root"]).rglob("*.onnx"))) > 0, "Offline embedding ONNX model missing.")
    require(read(PLUGIN / "plugin.json")["version"] == info["plugin_version"] == "0.1.15", "Plugin version mismatch.")
    require(read(PLUGIN / ".claude-plugin/plugin.json")["version"] == info["plugin_version"], "Claude plugin version mismatch.")
    report = {"ok": True, "state": str(state), "plugin_version": info["plugin_version"],
              "sfx_style_version": profile["version"], "zoom_style_version": zoom["version"],
              "hook_style_version": hook["version"], **counts, "sfx_receipts": len(memory.get("receipts", [])),
              "mp3_catalog": len(catalog), "history_files": len(list((state / "history").glob("*.json"))),
              "selected_state_writes": False, "capcut_project_writes": False,
              "creative_cross_host_equivalence_measured": False, "runtime": probe_runtime(state, cfg, runtime)}
    if args.verify_files:
        report["file_hashes_verified"] = verify_manifest(args.verify_files.resolve())
        report["manifest_mutable_file_checked_structurally"] = "runtime/env/pyvenv.cfg"
    if args.mcp:
        report["mcp"] = probe_mcp(state, cfg, runtime)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
