"""Check saved PPTX native body titles; does not inspect pixels or rendering."""
import argparse
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from validate_project import validate, resolve_mode, page_style, require


def verify(project, path):
    deck=validate(project)
    prs=Presentation(path)
    require(len(prs.slides)==len(deck['slides']), 'PPTX page count mismatch')
    for item, slide in zip(deck['slides'],prs.slides):
        style=page_style(deck,item)
        if item.get('type','content')!='content' or resolve_mode(deck,item)!='layered' or not style.get('show_title',True): continue
        matches=[s for s in slide.shapes if s.has_text_frame and s.text==item['title']]
        require(len(matches)==1,'Missing or duplicate native title: '+str(item['id']))
        title=matches[0]
        require(all(abs(a-Inches(b))<=2 for a,b in zip([title.left,title.top,title.width,title.height],style['title_box'])), 'Native title geometry mismatch')
        for paragraph in title.text_frame.paragraphs:
            f=paragraph.font
            require(f.name==style.get('title_font',style['font']) and f.size==Pt(style.get('title_size',30)), 'Native title font mismatch')
            require(f.bold==style.get('title_bold',False) and str(f.color.rgb)==style.get('title_color',style['color']).upper(), 'Native title appearance mismatch')
            if 'title_align' in style:
                require(paragraph.alignment=={'left':PP_ALIGN.LEFT,'center':PP_ALIGN.CENTER,'right':PP_ALIGN.RIGHT}[style['title_align']], 'Native title alignment mismatch')
    return True


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--pptx',required=True);a=p.parse_args()
    verify(a.project,a.pptx)
    print('Saved PPTX native title structure passed; image text and spacing require rendered review.')
