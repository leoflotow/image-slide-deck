import unittest,sys,json,copy,tempfile
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_project import validate_design,design_fingerprint
class DesignLockTests(unittest.TestCase):
 def test_lock_and_drift(self):
  with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
   root=Path(directory);Image.new('RGB',(20,20),'white').save(root/'ref.png')
   d=json.loads((Path(__file__).resolve().parents[1]/'assets/templates/deck.json').read_text(encoding='utf-8'))
   d['slides']=[copy.deepcopy(d['slides'][1])];d['status']['samples']='confirmed'
   d['body_design']={'layout':'canvas-local','reference_image':'ref.png','locked':True}
   d['body_design']['fingerprint']=design_fingerprint(root,d)
   validate_design(root,d,'ready')
   for change in [{'title_size':15},{'show_logo':False},{'title_margins':[0,0,0,0]}]:
    bad=copy.deepcopy(d);bad['slides'][0]['style']=change
    with self.assertRaises(ValueError):validate_design(root,bad,'ready')
   bad=copy.deepcopy(d);bad['layouts']['alias']=copy.deepcopy(bad['layouts']['canvas-local']);bad['layouts']['alias']['title_size']=13;bad['slides'][0]['layout']='alias'
   with self.assertRaises(ValueError):validate_design(root,bad,'ready')
   d['slides'][0]['title']='Long title\nAnother line';validate_design(root,d,'ready')
   Image.new('RGB',(20,20),'blue').save(root/'ref.png')
   with self.assertRaises(ValueError):validate_design(root,d,'ready')
if __name__=='__main__':unittest.main()
