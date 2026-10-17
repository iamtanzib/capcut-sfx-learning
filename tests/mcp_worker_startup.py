"""Regression: MCP child processes must not inherit/consume protocol stdin."""
import asyncio,json,os,sys,tempfile
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]
async def main():
    with tempfile.TemporaryDirectory() as temp:
        state=Path(temp)/'state';state.mkdir();drafts=Path(temp)/'drafts';project=drafts/'fixture';folder=project/'Timelines'/'T';folder.mkdir(parents=True)
        media=Path(temp)/'invalid-test.mp4';media.write_bytes(b'intentionally invalid fixture')
        cfg=json.loads((ROOT/'seed/config.json').read_text());cfg.update(draft_root=str(drafts),library=str(Path(temp)))
        (state/'config.json').write_text(json.dumps(cfg));(state/'data').mkdir();(state/'data/sound_catalog.json').write_text('[]')
        draft={'id':'T','duration':1_000_000,'materials':{'videos':[{'id':'v','path':str(media)}],'audios':[],'texts':[]},
            'tracks':[{'type':'video','segments':[{'material_id':'v','target_timerange':{'start':0,'duration':1_000_000},'source_timerange':{'start':0,'duration':1_000_000}}]}]}
        (folder/'draft_content.json').write_text(json.dumps(draft));(project/'Timelines/project.json').write_text(json.dumps({'timelines':[{'id':'T','name':'fixture'}]}))
        env={**os.environ,'SOUNDPILOT_STATE':str(state)}
        async with stdio_client(StdioServerParameters(command=sys.executable,args=[str(ROOT/'server.py')],env=env)) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize();result=await client.call_tool('prepare_batch',{'targets':[{'project':'fixture','timeline':'T'}]})
                assert not result.isError;batch=json.loads(result.content[0].text)['batch_id']
                status=None
                for _ in range(30):
                    await asyncio.sleep(.5);result=await client.call_tool('batch_status',{'batch_id':batch});status=json.loads(result.content[0].text)['jobs'][0]['status']
                    if status in ('failed','ready'):break
                assert status=='failed',f'Invalid-media worker should run and fail promptly, not stay queued: {status}'
                result=await client.call_tool('get_style_memory',{});assert not result.isError
                print(json.dumps({'worker_started':True,'invalid_fixture_rejected':True,'protocol_stdin_intact':True,'real_project_writes':False}))
asyncio.run(main())
