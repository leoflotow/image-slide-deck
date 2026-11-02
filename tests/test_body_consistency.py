import copy, json, sys, tempfile, unittest
from pathlib import Path
from PIL import Image
from pptx import Presentation
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_project import check_body_policy, design_fingerprint
from assemble_deck import assemble
from verify_pptx import verify
from describe_layout import describe

class BodyConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.deck=json.loads((ROOT/'assets/templates/deck.json').read_text(encoding='utf-8'))
        self.deck['body_design']['body_spacing']={'start_y':1.5,'tolerance':0.1} # explicit legacy opt-in
    def test_unlocked_mode_and_type_guards(self):
        for mutation in ({'mode':'full'},{'type':'boddy'},{'style':{'show_title':False}},{'body_spacing':{'start_y':3}}):
            d=copy.deepcopy(self.deck);d['slides'][1].update(mutation)
            with self.assertRaises(ValueError):check_body_policy(d)
        d=copy.deepcopy(self.deck);d['slides'][1].update(mode='full',body_design_exception=True)
        with self.assertRaises(ValueError):check_body_policy(d)
        d['slides'][1]['user_decision']='User explicitly requested this page full';check_body_policy(d)
        check_body_policy(self.deck) # special cover remains full
    def test_spacing_export_and_lock(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as t:
            d=self.deck;Image.new('RGB',(20,20)).save(Path(t)/'ref.png');d['body_design']['reference_image']='ref.png'
            old=design_fingerprint(t,d);d['body_design']['body_spacing']['start_y']=1.7
            self.assertNotEqual(old,design_fingerprint(t,d))
            self.assertEqual(describe(d,d['slides'][1])['body_spacing']['start_y'],1.7)
            d['body_design']['body_spacing']['start_y']=0.5
            with self.assertRaises(ValueError):check_body_policy(d)
    def test_separator_is_foreground_and_optional_spacing(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as t:
            p=Path(t);d=self.deck;d['body_design'].pop('body_spacing');d['slides']=d['slides'][1:];d['slides'][0]['image']='body.png'
            check_body_policy(d)
            info=describe(d,d['slides'][0]);self.assertNotIn('body_spacing',info);self.assertAlmostEqual(info['body_min_y'],1.3)
            Image.new('RGB',(1600,900),'lightblue').save(p/'body.png');(p/'deck.json').write_text(json.dumps(d),encoding='utf-8')
            prs=Presentation(assemble(p));shapes=list(prs.slides[0].shapes)
            line=next(i for i,s in enumerate(shapes) if s.name=='deck-title-separator')
            self.assertGreater(line,next(i for i,s in enumerate(shapes) if s.shape_type==13))
            self.assertLess(line,next(i for i,s in enumerate(shapes) if s.name=='deck-title'))
    def test_separator_changes_invalidate_design(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as t:
            p=Path(t);Image.new('RGB',(10,10)).save(p/'ref.png');d=self.deck;d['body_design']['reference_image']='ref.png'
            old=design_fingerprint(p,d);d['layouts']['canvas-local']['title_separator']['box'][1]=1.3
            self.assertNotEqual(old,design_fingerprint(p,d))

    def test_saved_pptx_title_removed_or_modified(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as t:
            p=Path(t);d=self.deck;d['slides']=d['slides'][1:];d['slides'][0]['image']='body.png'
            Image.new('RGB',(1600,900),'lightblue').save(p/'body.png');(p/'deck.json').write_text(json.dumps(d),encoding='utf-8')
            path=assemble(p);verify(p,path)
            prs=Presentation(path);shape=next(s for s in prs.slides[0].shapes if s.name=='deck-title')
            shape.text='wrong';prs.save(path)
            with self.assertRaises(ValueError):verify(p,path)

if __name__=='__main__':unittest.main()

