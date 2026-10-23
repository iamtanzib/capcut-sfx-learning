"""Token cost of Claude Code sessions in this project, from the local transcripts.

Usage: python session_cost.py [session-id-prefix ...] [--last N] [--turns]
Cost is in US dollars at list API prices per 1M tokens (Claude Code plans bill differently,
but the proportions are the same). Use it before/after a workflow change.
"""
import argparse, collections, glob, json, os

ROOT = os.path.expanduser('~/.claude/projects')
# $ per 1M tokens: input, cache read, cache write (5 min), output. Caches are per model.
PRICE = {'opus': (4, .2, 5, 20), 'sonnet': (2, .2, 2.5, 10), 'haiku': (.1, .01, .125, .5)}
KEYS = ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens', 'output_tokens')
def weights(model):
    p = next((v for k, v in PRICE.items() if k in (model or '')), PRICE['opus'])
    return dict(zip(KEYS, (x / 1e6 for x in p)))

def turns(path):
    seen = collections.OrderedDict()
    for line in open(path, encoding='utf-8'):
        try: d = json.loads(line)
        except ValueError: continue
        m = d.get('message') or {}
        if d.get('type') != 'assistant' or not m.get('usage'): continue
        t = seen.setdefault(m.get('id'), {'usage': m['usage'], 'tools': [], 'model': m.get('model')})
        t['tools'] += [c['name'].split('__')[-1] for c in m.get('content', []) if c.get('type') == 'tool_use']
    return list(seen.values())

def main():
    p = argparse.ArgumentParser(); p.add_argument('ids', nargs='*'); p.add_argument('--last', type=int, default=5)
    p.add_argument('--turns', action='store_true'); a = p.parse_args()
    files = sorted(glob.glob(os.path.join(ROOT, '*Capcutauto*', '*.jsonl')), key=os.path.getmtime)
    files = [f for f in files if any(os.path.basename(f).startswith(i) for i in a.ids)] if a.ids else files[-a.last:]
    for f in files:
        rows = turns(f); total = collections.Counter(); cost = 0.
        for i, t in enumerate(rows):
            u = t['usage']; w = weights(t['model']); c = sum(u.get(k, 0) * w[k] for k in KEYS); cost += c
            total.update({k: u.get(k, 0) * w[k] for k in KEYS})
            if a.turns:
                ctx = u.get('input_tokens', 0) + u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0)
                print(f"  {i:3d} ctx {ctx/1000:6.0f}k out {u.get('output_tokens', 0):6d} ${c:6.3f} {','.join(t['tools'])[:90]}")
        share = {k: total[k] / cost for k in KEYS} if cost else {}
        print(f"{os.path.basename(f)[:8]} turns {len(rows)} cost ${cost:.2f} "
              f"(cache read {share.get('cache_read_input_tokens', 0):.0%}, cache write {share.get('cache_creation_input_tokens', 0):.0%}, "
              f"output {share.get('output_tokens', 0):.0%}) peak ctx {max((t['usage'].get('cache_read_input_tokens', 0) for t in rows), default=0)/1000:.0f}k")

if __name__ == '__main__':
    main()
