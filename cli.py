"""Tool-call fallback for hosts with shell access but no MCP connection."""
import argparse,json
import service as api
p=argparse.ArgumentParser();p.add_argument('tool');p.add_argument('--json',default='{}');p.add_argument('--input');args=p.parse_args()
params=json.loads(open(args.input,encoding='utf-8').read()) if args.input else json.loads(args.json)
allowed={'list_projects':api.s.list_projects,'prepare_batch':api.prepare_batch,'batch_status':api.status,'get_brief':api.get_brief,'get_batch_briefs':api.get_batch_briefs,'get_context':api.get_context,
    'exact_frame':api.exact_frame,'stage_plan':api.stage_plan,'audit_mix':api.audit_mix,'preflight_batch':api.preflight_batch,'apply_batch':api.apply_batch,
    'learn_revision':api.learn_revision,'get_style_memory':api.memory,'configure':api.configure,'get_context_batch':api.get_context_batch,
    'learn_zoom_style':api.learn_zoom_style,'prepare_zoom_batch':api.prepare_zoom_batch,'get_zoom_briefs':api.get_zoom_briefs,
    'get_zoom_context':api.get_zoom_context,'stage_zoom_plan':api.stage_zoom_plan,'preview_zoom_plan':api.preview_zoom_plan,
    'apply_zoom_batch':api.apply_zoom_batch,'learn_zoom_revision':api.learn_zoom_revision,
    'prepare_edit_batch':api.prepare_edit_batch,'get_edit_briefs':api.get_edit_briefs,'apply_edit_batch':api.apply_edit_batch,
    'learn_hook_style':api.learn_hook_style,'stage_hook_plan':api.stage_hook_plan,'preview_hook_plan':api.preview_hook_plan,
    'learn_hook_revision':api.learn_hook_revision,'analysis_cache_status':api.analysis_cache_status,'learn_edit_revision':api.learn_edit_revision}
if args.tool not in allowed:raise ValueError('Unknown tool.')
print(json.dumps(allowed[args.tool](**params),ensure_ascii=False,separators=(',',':')))
