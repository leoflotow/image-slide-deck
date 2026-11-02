import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
from PIL import Image
from pptx import Presentation
from pptx.enum.text import PP_ALIGN

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from assemble_deck import assemble
from validate_project import validate, page_style


class LayeredDesignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='image-slide-deck-test-', dir=Path.cwd())
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.deck = json.loads((ROOT/'assets/templates/deck.json').read_text(encoding='utf-8'))
        self.deck['logo'] = 'logo.png'
        self.deck['style']['composition'] = 'framed'
        # Alpha tests explicitly choose transparency; production default is matched.
        self.deck['style']['content_surface'] = 'transparent'
        self.deck['slides'] = [{'id':'1','type':'content','title':'Design test','mode':'layered','layout':'top-brand','image':'body.png'}]
        self.body()
        Image.new('RGBA',(200,65),(0,0,0,0)).save(self.root/'logo.png')
        Image.new('RGB',(1600,900),'#CCDDEE').save(self.root/'background.png')

    def body(self, layout='top-brand', opaque=False):
        box=self.deck['layouts'][layout]['content_box']
        size=(round(box[2]*100), round(box[3]*100))
        image=Image.new('RGBA',size,(0,0,0,0))
        image.paste((20,100,95,255),(size[0]//3,size[1]//3,size[0]*2//3,size[1]*2//3))
        if opaque: image=Image.new('RGB',size,'#F2F5F2')
        image.save(self.root/'body.png')

    def save(self):
        (self.root/'deck.json').write_text(json.dumps(self.deck),encoding='utf-8')

    def render(self):
        self.save()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return Presentation(assemble(self.root))

    def test_new_default_accepts_opaque_integrated_body(self):
        self.deck['style']['content_surface']='matched'
        self.body(opaque=True)
        slide=self.render().slides[0]
        self.assertEqual([s.text for s in slide.shapes if s.has_text_frame and s.text],['Design test','1 / 1'])

    def test_all_layouts_and_alpha_preserved(self):
        for name in ('top-brand','side-guide','editorial'):
            with self.subTest(layout=name):
                self.deck['slides'][0]['layout']=name
                self.body(name)
                slide=self.render().slides[0]
                pictures=[s for s in slide.shapes if s.shape_type==13]
                self.assertEqual(len(pictures),2)
                import io
                with Image.open(io.BytesIO(pictures[0].image.blob)) as embedded:
                    self.assertEqual(embedded.getchannel('A').getextrema(),(0,255))
                self.assertEqual(str(slide.background.fill.fore_color.rgb),self.deck['layouts'][name]['background'])

    def test_merge_and_independent_text(self):
        item=self.deck['slides'][0]
        item['style']={'title_align':'right','page_align':'center','title_color':'112233','page_color':'445566','title_font':'Arial','section_text':'Chapter','section_color':'667788','section_align':'center'}
        self.assertEqual(page_style(self.deck,item)['background'],'F2F5F2')
        slide=self.render().slides[0]
        texts={s.text:s for s in slide.shapes if s.has_text_frame and s.text}
        self.assertEqual(texts['Design test'].text_frame.paragraphs[0].alignment,PP_ALIGN.RIGHT)
        self.assertEqual(texts['1 / 1'].text_frame.paragraphs[0].alignment,PP_ALIGN.CENTER)
        self.assertEqual(str(texts['1 / 1'].text_frame.paragraphs[0].font.color.rgb),'445566')
        self.assertEqual(texts['Design test'].text_frame.paragraphs[0].font.name,'Arial')
        self.assertIn('Chapter',texts)

    def test_background_order_and_switches(self):
        self.deck['body_design'].pop('enforce_body_mode',None) # legacy supports hidden titles
        self.deck['slides'][0]['style']={'background_image':'background.png','show_title':False,'show_page':False,'show_logo':False,'section_text':'Chapter','show_section':False}
        slide=self.render().slides[0]
        self.assertEqual(slide.shapes[0].shape_type,13)
        self.assertEqual(slide.shapes[1].shape_type,9) # line under content
        self.assertFalse(any(s.has_text_frame for s in slide.shapes))
        self.assertEqual(len(slide.shapes),3)

    def test_matched_and_white_logo(self):
        self.body(opaque=True)
        Image.new('RGB',(200,65),'white').save(self.root/'logo.png')
        self.deck['slides'][0]['style']={'content_surface':'matched'}
        self.assertEqual(len([s for s in self.render().slides[0].shapes if s.shape_type==13]),2)

    def test_full_ignores_layered_chrome(self):
        item=self.deck['slides'][0]
        item.update(type='cover',mode='full',image='background.png',style={'background_image':'not-needed.png','section_text':'Hidden'})
        self.assertEqual(len(self.render().slides[0].shapes),1)

    def test_legacy_configuration(self):
        self.deck.pop('layouts')
        self.deck['style'].pop('content_surface')
        item=self.deck['slides'][0];item.pop('layout')
        self.body_legacy()
        self.assertEqual(len(self.render().slides[0].shapes),4)

    def body_legacy(self):
        Image.new('RGB',(1210,560),'white').save(self.root/'body.png')

    def test_invalid_and_fake_transparency(self):
        mutations=[{'title_align':'diagonal'},{'page_format':'{n.__class__}'},{'page_format':'{other}'},{'section_text':'Oops','section_box':[0.65,1.5,2,0.5]},{'accents':[{'type':'line','box':[0,0,0,0],'color':'123456'}]}]
        for override in mutations:
            with self.subTest(override=override):
                self.deck['slides'][0]['style']=override;self.save()
                with self.assertRaises(ValueError): validate(self.root)
        self.deck['slides'][0].pop('style');self.body(opaque=True);self.save()
        with self.assertRaisesRegex(ValueError,'alpha'):validate(self.root)
        Image.new('RGBA',(1200,545),(0,0,0,0)).save(self.root/'body.png')
        with self.assertRaisesRegex(ValueError,'alpha'):validate(self.root)

    def test_long_title_and_collision_protection(self):
        item=self.deck['slides'][0]
        item['title']='A deliberately longer title\nSecond line remains separate from the logo'
        item['style']={'title_box':[0.65,0.2,9.6,1.0],'title_size':24}
        slide=self.render().slides[0]
        shape=next(s for s in slide.shapes if s.has_text_frame and s.text==item['title'])
        self.assertEqual(len(shape.text_frame.paragraphs),2)
        item['style']['title_box']=[0.65,0.2,12,1.0];self.save()
        with self.assertRaisesRegex(ValueError,'Fixed elements overlap'):validate(self.root)

    def test_unknown_layout_and_missing_background(self):
        self.deck['slides'][0]['layout']='missing';self.save()
        with self.assertRaisesRegex(ValueError,'Unknown layout'):validate(self.root)
        self.deck['slides'][0]['layout']='top-brand'
        self.deck['slides'][0]['style']={'background_image':'future.png'};self.save()
        validate(self.root,'draft')
        with self.assertRaises(FileNotFoundError):validate(self.root)


class OverlayCompositionTests(unittest.TestCase):
    body = LayeredDesignTests.body
    save = LayeredDesignTests.save
    render = LayeredDesignTests.render
    def setUp(self):
        LayeredDesignTests.setUp(self)
        self.deck['slides'][0]['image']='background.png'
        self.deck['slides'][0]['style']={'composition':'overlay','content_surface':'matched'}

    # Inherited tests are exercised separately with legacy framed fixtures.
    def test_new_template_prefers_overlay(self):
        from validate_project import image_box, composition
        deck=json.loads((ROOT/'assets/templates/deck.json').read_text(encoding='utf-8'))
        item=deck['slides'][1]
        self.assertEqual(composition(page_style(deck,item)),'overlay')
        self.assertEqual(image_box(deck,item),[0,0,*deck['size']])

    def test_old_missing_composition_keeps_framed(self):
        from validate_project import image_box
        self.deck['style'].pop('composition',None)
        self.deck['layouts']['top-brand'].pop('composition',None)
        item=self.deck['slides'][0];item['style'].pop('composition')
        self.assertEqual(image_box(self.deck,item),self.deck['layouts']['top-brand']['content_box'])
        slide=self.render().slides[0]
        self.assertGreater(next(s for s in slide.shapes if s.shape_type==13).top,0)

    def test_overlay_full_canvas_and_editable_title(self):
        from pptx.util import Inches
        slide=self.render().slides[0]
        body=next(s for s in slide.shapes if s.shape_type==13)
        self.assertLess(abs(body.left),10)
        self.assertLess(abs(body.top),10)
        self.assertLess(abs(body.width-Inches(self.deck['size'][0])),10)
        self.assertEqual([s.text for s in slide.shapes if s.has_text_frame and s.text],['Design test','1 / 1'])

    def test_overlay_reserved_collisions_still_rejected(self):
        self.deck['slides'][0]['overlays']=[{'image':'logo.png','box':[0.7,0.45,1,0.2]}]
        self.save()
        with self.assertRaisesRegex(ValueError,'Overlay overlaps reserved'):validate(self.root)
        self.deck['slides'][0].pop('overlays')
        self.deck['slides'][0]['style']['page_box']=self.deck['style']['title_box']
        self.save()
        with self.assertRaisesRegex(ValueError,'Fixed elements overlap'):validate(self.root)

    def test_overlay_without_content_box_and_derived_regions(self):
        from describe_layout import describe
        self.deck['style'].pop('content_box')
        self.deck['layouts']['top-brand'].pop('content_box')
        self.save();validate(self.root)
        report=describe(self.deck,self.deck['slides'][0])
        self.assertEqual(report['image_box_inches'],[0,0,*self.deck['size']])
        self.assertEqual({x['role'] for x in report['reserved_regions']},{'title','logo','page'})
        self.assertEqual(next(x['box_inches'] for x in report['reserved_regions'] if x['role']=='title'),self.deck['layouts']['top-brand']['title_box'])

    def test_overlay_disables_reservation_and_rejects_invalid_composition(self):
        from describe_layout import describe
        self.deck['slides'][0]['style'].update(show_page=False,show_logo=False)
        report=describe(self.deck,self.deck['slides'][0])
        self.assertEqual([x['role'] for x in report['reserved_regions']],['title'])
        self.deck['slides'][0]['style']['composition']='unknown';self.save()
        with self.assertRaisesRegex(ValueError,'Invalid composition'):validate(self.root)


if __name__=='__main__':unittest.main()

