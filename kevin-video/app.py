"""Small local-only review UI; one background worker prevents concurrent writes."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import threading
import urllib.parse
import uuid
import webbrowser

import soundpilot as sp

LOCK=threading.Lock()
STATE={'busy':False,'message':'Ready','result':None,'error':None}
TOKEN=uuid.uuid4().hex
POOL=ThreadPoolExecutor(max_workers=1)
PLANNER=sp.Planner(progress=lambda text: update(message=text))


def update(**kwargs):
    with LOCK:
        STATE.update(kwargs)


def start_job(operation):
    with LOCK:
        if STATE['busy']:
            raise ValueError('Another operation is still running.')
        STATE.update(busy=True,message='Working...',result=None,error=None)
    def run():
        try:
            result=operation()
            update(busy=False,message='Done',result=result)
        except Exception as exc:
            update(busy=False,message='Needs attention',error=str(exc))
    POOL.submit(run)


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass

    def reply(self,value,status=200):
        payload=json.dumps(value,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(payload))); self.send_header('Cache-Control','no-store')
        self.end_headers(); self.wfile.write(payload)

    def do_GET(self):
        parsed=urllib.parse.urlparse(self.path)
        if self.headers.get('Host') not in {'127.0.0.1:8765','localhost:8765'}:
            return self.reply({'error':'Local access only'},403)
        try:
            if parsed.path=='/':
                body=(sp.BASE/'ui.html').read_text(encoding='utf-8').replace('__TOKEN__',TOKEN).encode()
                self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body)))
                self.end_headers(); self.wfile.write(body)
            elif parsed.path=='/api/state':
                with LOCK: state=dict(STATE)
                self.reply(state)
            elif parsed.path=='/api/bootstrap':
                cfg=sp.config()
                catalog=sp.read_json(sp.DATA/'sound_catalog.json') if (sp.DATA/'sound_catalog.json').exists() else []
                summary=sp.read_json(sp.DATA/'training_summary.json') if (sp.DATA/'training_summary.json').exists() else []
                export=sp.read_json(sp.OUTPUTS/'latest_export.json') if (sp.OUTPUTS/'latest_export.json').exists() else None
                plan=sp.read_json(sp.OUTPUTS/'demo_plan.json') if (sp.OUTPUTS/'demo_plan.json').exists() else None
                evaluation=sp.read_json(sp.DATA/'evaluation.json') if (sp.DATA/'evaluation.json').exists() else None
                self.reply({'projects':sp.list_projects(),'sounds':catalog,'summary':summary,'export':export,'plan':plan,'evaluation':evaluation,'config':{'default_project':cfg['default_project'],'default_timeline':cfg['default_timeline'],'library':cfg['library']}})
            elif parsed.path=='/audio':
                name=urllib.parse.parse_qs(parsed.query).get('name',[''])[0]
                sounds=sp.read_json(sp.DATA/'sound_catalog.json')
                sound=next((s for s in sounds if s['name']==name),None)
                if not sound:
                    return self.reply({'error':'Sound not found'},404)
                path=Path(sound['path']); size=path.stat().st_size
                lo=0; hi=size-1; status=200
                rng=self.headers.get('Range')
                if rng:
                    import re
                    match=re.fullmatch(r'bytes=(\d+)-(\d*)',rng)
                    if match:
                        lo=int(match[1]); hi=min(int(match[2]) if match[2] else size-1,size-1); status=206
                    if lo>hi or lo>=size:
                        return self.reply({'error':'Range outside file'},416)
                self.send_response(status); self.send_header('Content-Type','audio/mpeg'); self.send_header('Accept-Ranges','bytes'); self.send_header('Content-Length',str(hi-lo+1))
                if status==206: self.send_header('Content-Range',f'bytes {lo}-{hi}/{size}')
                self.end_headers()
                with path.open('rb') as f:
                    f.seek(lo); self.wfile.write(f.read(hi-lo+1))
            else:
                self.reply({'error':'Not found'},404)
        except Exception as exc:
            self.reply({'error':str(exc)},400)

    def do_POST(self):
        if self.headers.get('Host') not in {'127.0.0.1:8765','localhost:8765'} or self.headers.get('X-SoundPilot-Token')!=TOKEN:
            return self.reply({'error':'Local review UI required'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>2_000_000: raise ValueError('Request too large')
            data=json.loads(self.rfile.read(length) or b'{}')
            if self.path=='/api/train': action=PLANNER.train
            elif self.path=='/api/plan': action=lambda:PLANNER.plan(data['project'],data['timeline'],float(data.get('density',1)))
            elif self.path=='/api/context':
                from context_pipeline import prepare
                action=lambda:prepare(data['project'],data['timeline'],progress=lambda text:update(message=text))
            elif self.path=='/api/evaluate': action=PLANNER.evaluate
            elif self.path=='/api/export':
                plan=data['plan']; sp.write_json(sp.OUTPUTS/'reviewed_plan.json',plan)
                action=lambda:sp.export_copy(plan,bool(data.get('replace_existing')))
            elif self.path=='/api/register': action=lambda:sp.register_export(data['path'])
            elif self.path=='/api/install': action=lambda:sp.install_into_empty_timeline(data['path'],data['project'],data['timeline'])
            else: return self.reply({'error':'Not found'},404)
            start_job(action); self.reply({'started':True})
        except Exception as exc:
            self.reply({'error':str(exc)},400)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--no-browser',action='store_true'); args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',8765),Handler)
    print('SoundPilot: http://127.0.0.1:8765',flush=True)
    if not args.no_browser: webbrowser.open('http://127.0.0.1:8765')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close(); POOL.shutdown(wait=False)
