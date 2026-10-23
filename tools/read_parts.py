"""Split a large saved MCP result (or live style JSON) into a few Read-sized parts, losslessly.

Usage: python read_parts.py <saved tool-result .txt or state .json> [--chars 60000]
Prints one JSON line: manifest path, part paths, part_count. Read EVERY part, all in one
message (parallel Read calls), instead of many small sequential windows.

Newlines are inserted only between JSON tokens (after a comma outside strings), so the
concatenated parts are still the same JSON document; the script asserts that. A string
longer than the line limit is the only place a line breaks inside a value, and the manifest
counts those breaks.
"""
import argparse, hashlib, json, os, sys

LINE = 1500  # Read truncates long physical lines; stay well under its limit.

def decode(text):
    """Unwrap a top-level MCP text-content envelope; otherwise return the JSON as is."""
    value = json.loads(text)
    if isinstance(value, list) and value and all(isinstance(v, dict) and v.get('type') == 'text' for v in value):
        return json.loads(''.join(v['text'] for v in value)), True
    return value, False

def lines_of(compact):
    out, line, in_str, esc, hard = [], [], False, False, 0
    for ch in compact:
        line.append(ch)
        if in_str:
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == '"': in_str = False
        elif ch == '"': in_str = True
        n = len(line)
        if (not in_str and ch == ',' and n >= LINE - 300) or n >= LINE:
            if in_str or ch != ',': hard += 1
            out.append(''.join(line)); line = []
    if line: out.append(''.join(line))
    return out, hard

def main():
    p = argparse.ArgumentParser(); p.add_argument('input'); p.add_argument('--chars', type=int, default=45000)
    a = p.parse_args()
    src = os.path.abspath(os.path.expanduser(a.input))
    raw = open(src, encoding='utf-8').read()
    value, envelope = decode(raw)
    compact = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    sha = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    state = os.environ.get('SOUNDPILOT_STATE') or os.path.expanduser('~/SoundPilotLearning')
    dest = os.path.join(state, 'readable', f"{os.path.splitext(os.path.basename(src))[0][:60]}-{sha[:12]}")
    os.makedirs(dest, exist_ok=True)
    rows, hard = lines_of(compact)
    parts, cur, size = [], [], 0
    for r in rows:
        if cur and size + len(r) + 1 > a.chars: parts.append(cur); cur, size = [], 0
        cur.append(r); size += len(r) + 1
    if cur: parts.append(cur)
    paths = []
    for i, rows_ in enumerate(parts, 1):
        path = os.path.join(dest, f'part-{i:02d}-of-{len(parts):02d}.txt')
        open(path, 'w', encoding='utf-8').write('\n'.join(rows_) + '\n'); paths.append(path)
    joined = ''.join(open(x, encoding='utf-8').read() for x in paths)
    # Exact reconstruction: dropping the inserted newlines gives the compact text back.
    assert joined.replace('\n', '') == compact, 'parts do not reconstruct the source'  # compact JSON has no raw newlines
    if not hard: assert json.loads(joined) == value, 'parts are not the same JSON'
    manifest = {'source': src, 'source_sha256': sha, 'decoded_transport_payload': envelope, 'chars': len(compact),
        'part_count': len(paths), 'parts': paths, 'line_limit': LINE, 'breaks_inside_strings': hard,
        'reading_rule': 'Read every part (all in one message). Newlines sit between JSON tokens; '
                        + ('concatenate parts as-is to get the source JSON.' if not hard else
                           f'{hard} line break(s) fall inside long strings; join lines without separators there.')}
    mpath = os.path.join(dest, 'MANIFEST.json'); json.dump(manifest, open(mpath, 'w', encoding='utf-8'), indent=1)
    print(json.dumps({'manifest': mpath, 'part_count': len(paths), 'parts': paths, 'breaks_inside_strings': hard}))

if __name__ == '__main__':
    sys.exit(main())
