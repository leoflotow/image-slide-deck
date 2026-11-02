"""Run only after the user confirms complete samples."""
import argparse,json
from pathlib import Path
from validate_project import design_fingerprint,validate
p=argparse.ArgumentParser();p.add_argument('--project',required=True);a=p.parse_args();root=Path(a.project)
d=json.loads((root/'deck.json').read_text(encoding='utf-8'))
if d.get('status',{}).get('samples')!='confirmed':p.error('User sample confirmation must be recorded first')
d['body_design']['fingerprint']=design_fingerprint(root,d);d['body_design']['locked']=True
# Check consistency before writing any changed configuration.
from validate_project import validate_design
validate_design(root,d,'draft')
(root/'deck.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Body design locked; prior configuration approval must come from user.')
