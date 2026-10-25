#!/usr/bin/env python3
"""P0 bounded metadata-only SkillCorner file inventory. Python stdlib only.
Usage: python p0_inventory.py '/Users/fadihaddad/Documents/GitHub/SkillCorner_opendata_soccer'
No data modified; does not ingest all match tracking/pose data or upload anything.
"""
import csv, json, sys
from pathlib import Path
ROOT = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.cwd()
base=ROOT/'data'/'matches'
if not base.is_dir(): raise SystemExit(f'Not found: {base}')
required=('match.json','tracking_extrapolated.jsonl','dynamic_events.csv','phases_of_play.csv')
ids=sorted(p.name for p in base.iterdir() if p.is_dir() and p.name.isdigit())
rows=[]
for ident in ids:
    d=base/ident
    result={'match_id':ident}
    for suffix in required:
        f=d/f'{ident}_{suffix}'
        result[suffix+'_bytes']=f.stat().st_size if f.is_file() else None
        if f.is_file():
            try:
                if suffix.endswith('csv'):
                    with f.open(newline='', encoding='utf-8-sig') as h:
                        rd=csv.reader(h); result[suffix+'_columns']=' | '.join(next(rd))
                        result[suffix+'_first_row']=' | '.join(next(rd,[]))[:350]
                elif suffix=='match.json':
                    with f.open(encoding='utf-8') as h: result[suffix+'_keys']=' | '.join(json.load(h).keys())
                else:
                    with f.open(encoding='utf-8') as h:
                        first=next((l for l in h if l.strip()),'')
                    result[suffix+'_keys']=' | '.join(json.loads(first).keys()) if first else 'EMPTY'
            except Exception as e: result[suffix+'_ERROR']=repr(e)
    rows.append(result)
pose=ROOT/'data'/'bodypose'
files=[{'path':str(x.relative_to(ROOT)),'bytes':x.stat().st_size} for x in pose.rglob('*') if x.is_file()] if pose.exists() else []
summary={'root':str(ROOT),'match_directories':len(ids),'complete_four_file_groups':sum(all(r.get(x+'_bytes',0) for x in required) for r in rows),'matches':rows,'bodypose_files':files}
out=ROOT/'P0_LOCAL_INVENTORY.json'
out.write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(f'Found {len(ids)} match directories, {summary["complete_four_file_groups"]} with four nonempty files; wrote {out}')
print('This verifies existence, headers and one record only—not full-file integrity or pose coverage.')
