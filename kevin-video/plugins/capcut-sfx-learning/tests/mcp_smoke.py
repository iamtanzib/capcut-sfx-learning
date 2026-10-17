"""Actual stdio initialize/discovery/read-only tool call (no project writes)."""
import asyncio,json,sys,os
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]
async def main():
    params=StdioServerParameters(command='powershell',args=['-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'launch.ps1')])
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            startup=await session.initialize();assert '$defaults' in startup.instructions
            listing=await session.list_tools();names=[t.name for t in listing.tools]
            assert len(names)==31 and 'get_context_batch' in names and 'prepare_edit_batch' in names and 'stage_hook_plan' in names
            edit=next(t for t in listing.tools if t.name=='prepare_edit_batch');assert edit.inputSchema['properties']['mode']['default']=='full_combo'
            prepare=next(t for t in listing.tools if t.name=='prepare_batch')
            assert prepare.inputSchema['properties']['include_zoom']['default'] is True
            stage=next(t for t in listing.tools if t.name=='stage_plan')
            assert 'zooms' in stage.inputSchema['properties']
            for name in ('apply_batch','apply_zoom_batch','apply_edit_batch'):
                assert next(t for t in listing.tools if t.name==name).inputSchema['properties']['auto_close']['default'] is True
            result=await session.call_tool('list_projects',{});assert not result.isError
            style=await session.call_tool('get_style_memory',{});assert not style.isError
            assert '\n' not in style.content[0].text # ensure minified transport text
            assert '$defaults' in style.content[0].text # real inherited-table memory transport
            if os.environ.get('SOUNDPILOT_SMOKE_JOB'):
                pooled=await session.call_tool('get_context_batch',{'job_id':os.environ['SOUNDPILOT_SMOKE_JOB'],'windows':[{'start':4,'end':7},{'start':5,'end':8}]})
                assert not pooled.isError and '\n' not in pooled.content[0].text
            print(json.dumps({'transport':'stdio','tools':names,'list_projects_ok':True,'minified_text':True,'writes_to_capcut':False},indent=2))
asyncio.run(main())
