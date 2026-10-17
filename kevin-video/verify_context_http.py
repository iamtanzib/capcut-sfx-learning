"""Local HTTP smoke test without browser/computer automation."""
import json
import re
import time
import urllib.request
import soundpilot as s

root='http://127.0.0.1:8765'
page=urllib.request.urlopen(root).read().decode()
assert 'Prepare context for Codex' in page
token=re.search(r"const TOKEN='([^']+)'",page).group(1)
request=urllib.request.Request(root+'/api/context',data=json.dumps({'project':'0928','timeline':'Timeline 12'}).encode(),
    headers={'Content-Type':'application/json','X-SoundPilot-Token':token},method='POST')
assert json.load(urllib.request.urlopen(request))['started']
for _ in range(40):
    state=json.load(urllib.request.urlopen(root+'/api/state'))
    if not state['busy']:break
    time.sleep(.25)
assert not state['busy'], 'Local context worker did not complete'
assert not state['error'], state['error']
result=state['result']
assert result['old_sfx_used_as_input'] is False
assert 'Timeline 11' in result['excluded_style_timelines']
print('HTTP_CONTEXT_OK',{'seconds':result['seconds'],'duplicate_reference_excluded':True})
s.write_json(s.OUTPUTS/'http_verification.json',{'success':True,'context_route':True,'default_model':result['model'],
    'duplicate_reference_excluded':True,'computer_control_used':False})
