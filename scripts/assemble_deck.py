import argparse
from pathlib import Path
from datetime import datetime
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from validate_project import validate, page_style, page_logo, resolve_mode, page_number, image_box


def picture(slide, path, box):
    x, y, w, h = box
    with Image.open(path) as image:
        iw, ih = image.size
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    return slide.shapes.add_picture(str(path), Inches(x + (w-pw)/2), Inches(y + (h-ph)/2), width=Inches(pw), height=Inches(ph))


def text(slide, value, box, style, role, default_size):
    shape = slide.shapes.add_textbox(*(Inches(v) for v in box))
    frame = shape.text_frame
    frame.word_wrap = True
    if role+'_margins' in style:
        frame.margin_left,frame.margin_top,frame.margin_right,frame.margin_bottom = (Inches(v) for v in style[role+'_margins'])
    for n, line in enumerate(value.split('\n')):
        paragraph = frame.paragraphs[0] if n == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.font.name = style.get(role+'_font', style['font'])
        paragraph.font.size = Pt(style.get(role+'_size', default_size))
        paragraph.font.color.rgb = RGBColor.from_string(style.get(role+'_color', style['color']))
        paragraph.font.bold = style.get(role+'_bold', False)
        if role+'_align' in style:
            paragraph.alignment = {'left': PP_ALIGN.LEFT, 'center': PP_ALIGN.CENTER, 'right': PP_ALIGN.RIGHT}[style[role+'_align']]
    shape.name = 'deck-'+role
    return shape


def decorations(slide, style):
    for item in style.get('accents', []):
        x, y, w, h = item['box']
        if item['type'] == 'line':
            shape = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y), Inches(x+w), Inches(y+h))
            shape.line.color.rgb = RGBColor.from_string(item['color'])
            shape.line.width = Pt(item.get('width', 1))
        else:
            shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor.from_string(item['color'])
            shape.line.fill.background()
        shape._element.spPr.append(OxmlElement('a:effectLst'))
        for effect in shape._element.xpath('.//a:effectRef'):
            effect.set('idx', '0')


def assemble(project):
    root = Path(project)
    deck = validate(root)
    prs = Presentation()
    width, height = deck['size']
    prs.slide_width, prs.slide_height = Inches(width), Inches(height)
    for n, item in enumerate(deck['slides'], 1):
        style = page_style(deck, item)
        mode = resolve_mode(deck, item)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(style['background'])
        if mode == 'layered':
            if style.get('background_image'):
                picture(slide, root/style['background_image'], [0, 0, width, height])
            decorations(slide, style)
        picture(slide, root/item['image'], image_box(deck, item, style))
        for overlay in item.get('overlays', []):
            picture(slide, root/overlay['image'], overlay['box'])
        if mode == 'layered':
            if style.get('title_separator'):
                before=len(slide.shapes)
                decorations(slide, {'accents':[{'type':'line', **style['title_separator']}]})
                slide.shapes[before].name='deck-title-separator'
            if style.get('show_title', True):
                text(slide, item['title'], style['title_box'], style, 'title', 30)
            if style.get('show_page', True):
                text(slide, page_number(style, n, len(deck['slides'])), style['page_box'], style, 'page', 12)
            if style.get('show_section', True) and style.get('section_text'):
                text(slide, style['section_text'], style['section_box'], style, 'section', 12)
            logo = page_logo(deck, item)
            if logo and style.get('show_logo', True):
                picture(slide, root/logo, style['logo_box'])
    out = root/'output'
    out.mkdir(exist_ok=True)
    target = out/('deck-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.pptx')
    prs.save(target)
    from verify_pptx import verify
    verify(root, target)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    print(assemble(parser.parse_args().project))
