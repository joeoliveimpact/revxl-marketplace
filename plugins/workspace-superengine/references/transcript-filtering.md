# Transcript filtering — the conversation layer, not the file

Read this when `/session-continue` is about to read a session transcript. It is the filter and the reason for it. **Never dump this file at the user.**

---


**Filter it. Never read the raw `.jsonl`.** Keep only `message.content` blocks of type `text`, from roles `user` and `assistant`. Drop `tool_use`, `tool_result` and `thinking` blocks entirely.

That filter is the difference between cheap and unaffordable. **Measured on one real session: a 0.90 MB transcript held 29.6 KB of actual conversation ... 3.2% of the file.** The other 97% was tool plumbing: git output, file reads, JSON payloads. None of it belongs in a kickoff prompt.

```bash
# Code environment. Conversation layer only, in order.
python -c "
import json,sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')   # Windows: stdout defaults to cp1252 and dies on any non-Latin-1 char
for line in open(sys.argv[1],encoding='utf-8',errors='replace'):
    try: d=json.loads(line)
    except: continue
    m=d.get('message') or {}
    c=m.get('content')
    if isinstance(c,str): print(m.get('role','?').upper(),':',c); continue
    if not isinstance(c,list): continue
    for b in c:
        if isinstance(b,dict) and b.get('type')=='text':
            print(m.get('role','?').upper(),':',b.get('text',''))
" <transcript path>
```

**Cowork:** no Bash. Say the transcript could not be filtered and build the prompt from the files alone, with the transcript path still cited in the read order so tomorrow's session can open it.

**No `**Session log:**` line, or the path is not on disk:** proceed without it. This is a soft degrade, not a thin flag ... the transcript enriches the prompt, it does not carry a required field. Say one line that it was unavailable.
