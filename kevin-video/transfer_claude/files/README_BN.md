# CapCut SFX Learning → Claude Code

এটি Srijon-এর বর্তমান CapCut SFX Learning-এর সম্পূর্ণ স্থানীয় workflow transfer package। Snapshot: **১৩ অক্টোবর ২০২৬, Asia/Dhaka**। Plugin **0.1.15**; SFX memory **v28 / 428 examples**, zoom memory **v14 / 15 reference timelines / 127 events**, hook memory **v8 / 17 references**। চূড়ান্ত সংখ্যা ও file inventory `BUNDLE_INFO.json` এবং manifest-এ আছে। পুরোনো plugin-এর v16 seed-এর পরিবর্তে বর্তমান শেখা memory এই package-এ দেওয়া হয়েছে।

একই PC-তে Claude Code ও Codex একই engine, sound library, model এবং durable memory ব্যবহার করতে পারে। Claude আলাদা model হওয়ায় প্রতিটি creative choice হুবহু এক হবে—এমন পরিমাপ করা হয়নি। তবে আগের শেখা correction, gain/timing policy, workflow ও native CapCut লেখার নিয়ম transfer করা হয়েছে।

## সবচেয়ে সহজ setup: বর্তমান Windows PC

1. ZIP সম্পূর্ণ extract করুন। স্থায়ী folder বেছে নিন, যেমন `C:\CapCut-Claude`। ZIP-এর ভেতর থেকে script চালাবেন না।
2. Native Windows Claude Code install করে নিজের account-এ sign in করুন। পদ্ধতি `docs/SETUP.md`-এ আছে।
3. Extracted folder-এর `INSTALL_CLAUDE_CODE.bat` চালান। বর্তমান `SoundPilotLearning` state/runtime/library/model/draft folder বৈধ থাকলে installer সেগুলো share করবে; snapshot দিয়ে বর্তমান শেখা memory replace করবে না।
4. `VERIFY.bat` চালান। বাড়তি read-only protocol check-এর জন্য PowerShell-এ চালান:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\VERIFY.ps1 -Mcp
   ```

5. `START_CLAUDE_CODE.bat` চালান। নতুন session-এ `/mcp` দিয়ে `capcut-sfx-learning` connection দেখুন, তারপর `/capcut-sfx-learning` invoke করুন। প্রথমে saved project list নিতে বলুন।

Claude-এর প্রথম prompt হিসেবে ব্যবহার করুন:

> এই folder-এর CLAUDE.md এবং capcut-sfx-learning skill পুরো পড়ো। বর্তমান local memory ব্যবহার করো। আগে saved projects ও stable timeline IDs দেখাও। আমার দেওয়া project/timeline-এ full combo edit করবে: SFX, reaction zoom এবং native intro text hook। পুরো দুই speaker stream ও cue timing যাচাই করবে; audio, zoom framing ও hook preview review করে apply করবে। Apply-এর আগে স্বাভাবিকভাবে CapCut close করার অনুমতি আছে; dialog/refusal হলে থামবে।

Project/timeline না দেওয়া পর্যন্ত edit করবে না। পুরোনো conversation-এর timeline ধরে নেওয়া যাবে না।

## অন্য Windows PC অথবা আলাদা পরীক্ষার state

Portable Python, বর্তমান dependency files, FFmpeg/ffprobe, offline models এবং sound assets package-এ আছে। অন্য PC-তে original video media ও নিজের CapCut drafts আলাদা করে রাখতে হবে। `EXTERNAL_INPUTS.json`-এ source paths এবং missing historical paths আছে। Package-এর `reference-projects` হল native project metadata archive; এটি নতুন PC-তে সব original footage অথবা স্বয়ংক্রিয় draft restore নয়।

নিজের existing CapCut draft root ব্যবহার করে PowerShell-এ:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\INSTALL_CLAUDE_CODE.ps1 -UsePortable -StateRoot 'C:\CapCut-Claude-State' -DraftRoot 'C:\Users\YOU\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft'
```

নতুন `StateRoot` ব্যবহার করলে Codex-এর active state অপরিবর্তিত রেখে পরীক্ষা করা যায়। Installer bundled file paths rebase করে, library rescan করে, memory/history restore করে। কোনো existing state-এ equal/newer memory থাকলে component অনুযায়ী সেটিই রাখা হয়। পুরোনো unfinished job সরাসরি apply না করে নতুন preparation/review করতে হবে।

## ZIP-এ যা আছে

| Folder/file | উদ্দেশ্য |
|---|---|
| `plugins/capcut-sfx-learning/` | বর্তমান engine, 31 MCP tools, CLI, skill ও সব workflow/schema reference, tests, release notes, font |
| `state/` | বর্তমান SFX/zoom/hook memory, learned rules/examples, frozen jobs, revision receipts, cached review evidence |
| `runtime/` | tested Windows x64 Python, environment/dependencies, FFmpeg/ffprobe |
| `models/` | offline speech/analysis model cache |
| `library/`, `assets/` | স্থানীয় sound library, referenced external sounds/fonts; duplicate aliases inventory-তে আছে |
| `reference-projects/` | saved native draft JSON/font metadata, live CapCut-এ import করা হয়নি |
| `reports/` | আগের update/revision/verification reports ও archives |
| `development-source/` | workspace scripts, config, tests, vendor ও development documents |
| `migration/` | launcher, state restore, health verification ও migration support |
| `CLAUDE.md`, `docs/` | Claude-কে workflow বুঝতে দেওয়া নির্দেশনা, setup ও troubleshooting |
| `BUNDLE_INFO.json`, `EXTERNAL_INPUTS.json`, `SOURCE_PARITY.json` | snapshot facts, external media inventory ও source parity evidence |

Installer-এর আগে দেওয়া ZIP SHA-256-এর সঙ্গে archive-এর hash মিলিয়ে নিন। PowerShell-এর `Get-FileHash -Algorithm SHA256 -LiteralPath 'YOUR_BUNDLE.zip'` ব্যবহার করতে পারেন; placeholder filename বদলাবেন। Installer-এর পরে `VERIFY.ps1 -Files -Mcp` দিয়ে payload/runtime/protocol পরীক্ষা করুন। `runtime/env/pyvenv.cfg` এবং local install records installation-এর সময় বদলানো স্বাভাবিক; verifier-এর output পড়ুন।

## ব্যবহার ও নতুন শেখা update

`full combo edit`, `just sfx`, `just zoom`, `just text hook` বললে সংশ্লিষ্ট mode ব্যবহৃত হয়। এক batch-এ সর্বোচ্চ পাঁচটি video timeline। সাত দিনের cache compatible media analysis reuse করে; memory ও revision history durable থাকে। Cache expire হলে প্রয়োজনীয় local analysis আবার চলবে। অন্য PC-তে absolute paths বা media timestamps বদলালে নতুন preparation প্রয়োজন হতে পারে; archive-এর frozen snapshot/hash বদলে cache বৈধ দেখানো যাবে না।

নিজে edit ঠিক করার পর Claude-কে বলুন:

> আমি project …, timeline … revise করেছি। original job/batch ID …-এর frozen prediction-এর সঙ্গে compare করে আমার SFX/zoom/hook revision learn করো; কী correction শেখা হল এবং timing বনাম association score আলাদা করে বলো।

একই `StateRoot` share করলে Claude-তে শেখা নতুন correction Codex থেকেও দেখা যাবে। ভিন্ন isolated state-এর শেখা update নিজে share/import করতে হবে; দুই state স্বয়ংক্রিয়ভাবে merge হয় না। এই ZIP একটি তারিখের snapshot; পরের learning স্বয়ংক্রিয়ভাবে ZIP-এর ভেতর যোগ হবে না।

## প্রয়োজনীয় সীমা ও সুরক্ষা

Account login/API keys/credentials অন্তর্ভুক্ত নেই। Plugin কোনো paid speech/inference API চায় না; Claude Code-এর নিজস্ব account/usage আলাদা। Original source videos, live CapCut executable এবং সম্পূর্ণ video project backup এই package-এ অন্তর্ভুক্ত নেই। একই PC-তে বিদ্যমান input paths ব্যবহার করুন; অন্য PC-তে footage copy/relink করুন।

Installer native CapCut projects edit করে না। Apply plan/audit validate করে স্বাভাবিক window-close request দেয়, process exit নিশ্চিত করে এবং শেষ autosave-এর পরে source আবার validate করে। Force-kill বা save/export dialog-এর automatic response নেই। Existing manual SFX এবং filled manual hook protected; clean target প্রয়োজন হলে নতুন timeline তৈরি করুন।

Exact-frame preview source frame; CapCut-এর overlays/compositing দেখায় না। Audio audit-এর peak pass মানেই শ্রবণগত বা creative correctness নয়। Audio শোনা সম্ভব না হলে সেই review unverified বলতে হবে। নতুন video-তে নিজের review দিয়েই creative quality যাচাই করুন।

বিস্তারিত: `docs/SETUP.md`, `docs/TROUBLESHOOTING.md`, `docs/WORKFLOW.md`, `docs/FILE_MAP.md`, `examples/`, skill-এর `references/` এবং বর্তমান `plugins/capcut-sfx-learning/CHANGELOG.md`। ঐতিহাসিক reports-এর পুরোনো version/count-কে বর্তমান snapshot ধরে ব্যবহার করবেন না।
