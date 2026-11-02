import argparse
import json
import math
import re
import warnings
import string
import hashlib
from pathlib import Path
from PIL import Image


def page_style(deck, slide):
    name = slide.get('layout')
    layouts = deck.get('layouts', {})
    require(name is None or name in layouts, f'Unknown layout: {name}')
    return {**deck['style'], **(layouts[name] if name is not None else {}), **slide.get('style', {})}


def page_logo(deck, slide):
    return slide.get('logo', deck.get('logo'))


def resolve_mode(deck, slide):
    if 'mode' in slide:
        return slide['mode']
    default = deck.get('mode', 'layered')
    if default == 'layered' and slide.get('type') in ('cover', 'contents', 'section', 'closing'):
        return 'full'
    return default


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_box(box, width, height):
    require(len(box) == 4 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in box), 'Invalid box')
    x, y, w, h = box
    require(x >= 0 and y >= 0 and w > 0 and h > 0 and x + w <= width + 1e-6 and y + h <= height + 1e-6, 'Box outside slide')


def overlaps(a, b):
    x, y, w, h = a
    bx, by, bw, bh = b
    return x < bx + bw and bx < x + w and y < by + bh and by < y + h


def composition(style):
    value = style.get('composition', 'framed')
    require(value in ('framed', 'overlay'), 'Invalid composition')
    return value


def image_box(deck, slide, style=None):
    style = page_style(deck, slide) if style is None else style
    if resolve_mode(deck, slide) == 'full' or composition(style) == 'overlay':
        return [0, 0, *deck['size']]
    return style['content_box']


def fixed_regions(deck, slide, style=None):
    style = page_style(deck, slide) if style is None else style
    if resolve_mode(deck, slide) != 'layered':
        return {}
    result = {}
    if style.get('show_title', True): result['title'] = style['title_box']
    if style.get('show_page', True): result['page'] = style['page_box']
    if style.get('show_section', True) and style.get('section_text'): result['section'] = style['section_box']
    if page_logo(deck, slide) and style.get('show_logo', True): result['logo'] = style['logo_box']
    return result


def check_image(path, box=None):
    with Image.open(path) as image:
        width, height = image.size
        image.verify()
    if box and abs((width / height) / (box[2] / box[3]) - 1) > 0.05:
        warnings.warn(f'{path}: image ratio differs from target; contain fit will leave empty space', stacklevel=2)


def page_number(style, n, total):
    pattern = style.get('page_format', '{n}')
    require(isinstance(pattern, str), 'Invalid page_format')
    for _, field, spec, conversion in string.Formatter().parse(pattern):
        require(field is None or (field in ('n', 'total') and not spec and conversion is None), 'page_format supports only {n} and {total}')
    return pattern.format(n=n, total=total)


def check_chrome(style, width, height):
    for role in ('title', 'page', 'section'):
        if role+'_margins' in style:
            margins=style[role+'_margins']
            require(isinstance(margins,list) and len(margins)==4 and all(isinstance(v,(int,float)) and math.isfinite(v) and v>=0 for v in margins),'Invalid '+role+'_margins')
        if role+'_color' in style:
            require(isinstance(style[role+'_color'], str) and re.fullmatch(r'[0-9A-Fa-f]{6}', style[role+'_color']), 'Invalid '+role+'_color')
        if role+'_align' in style:
            require(style[role+'_align'] in ('left', 'center', 'right'), 'Invalid '+role+'_align')
        if role+'_font' in style:
            require(isinstance(style[role+'_font'], str) and bool(style[role+'_font'].strip()), 'Invalid '+role+'_font')
        if role+'_size' in style:
            value = style[role+'_size']
            require(isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0, 'Invalid '+role+'_size')
        if role+'_bold' in style:
            require(isinstance(style[role+'_bold'], bool), 'Invalid '+role+'_bold')
    for key in ('show_title', 'show_page', 'show_logo', 'show_section'):
        require(key not in style or isinstance(style[key], bool), 'Invalid '+key)
    require(isinstance(style.get('section_text', ''), str), 'Invalid section_text')
    page_number(style, 1, 1)
    require(style.get('content_surface') in (None, 'transparent', 'matched', 'panel'), 'Invalid content_surface')
    separator=style.get('title_separator')
    if separator is not None:
        require(isinstance(separator,dict),'Invalid title_separator')
        check_chrome({'accents':[{'type':'line',**separator}]},width,height)
        require(separator.get('type','line')=='line' and separator['box'][3]==0,'Title separator must be horizontal')
        require(separator['box'][1]>=style['title_box'][1]+style['title_box'][3], 'Separator must be below title')
        gap=separator.get('clearance',0.12)
        require(isinstance(gap,(int,float)) and not isinstance(gap,bool) and math.isfinite(gap) and gap>=0 and separator['box'][1]+gap<height,'Invalid separator clearance')
    for item in style.get('accents', []):
        require(item.get('type') in ('line', 'rect'), 'Accents support line or rect only')
        require(isinstance(item.get('color'), str) and re.fullmatch(r'[0-9A-Fa-f]{6}', item['color']), 'Invalid accent color')
        box = item['box']
        if item['type']=='rect':
            check_box(box, width, height)
        else:
            require(len(box)==4 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in box), 'Invalid line box')
            x,y,w,h=box
            require(x>=0 and y>=0 and x+w>=0 and y+h>=0 and max(x,x+w)<=width and max(y,y+h)<=height and (w!=0 or h!=0), 'Line outside slide')
            value=item.get('width',1)
            require(isinstance(value,(int,float)) and math.isfinite(value) and value>0, 'Invalid line width')


def design_signature(project, deck, slide):
    style=page_style(deck,slide)
    data={'composition':composition(style),'size':deck['size']}
    for role, default_size in (('title',30),('page',12),('section',12)):
        data[role]={key:style.get(role+'_'+key, default) for key,default in [('font',style['font']),('size',default_size),('color',style['color']),('align','left'),('bold',False)]}
        data[role]['box']=style.get(role+'_box')
        data[role]['show']=style.get('show_'+role,True)
        data[role]['margins']=style.get(role+'_margins',[0.1,0.05,0.1,0.05])
    data['page_format']=style.get('page_format','{n}')
    data['logo_box']=style.get('logo_box')
    data['show_logo']=style.get('show_logo',True)
    logo=page_logo(deck,slide)
    data['logo_hash']=hashlib.sha256((Path(project)/logo).read_bytes()).hexdigest() if logo else None
    if 'title_separator' in style: data['title_separator']=style['title_separator']
    return data


def design_fingerprint(project,deck):
    design=deck['body_design']
    require(design['layout'] in deck.get('layouts',{}),'Unknown body design layout')
    canonical={'layout':design['layout'],'style':design.get('style',{})}
    data=design_signature(project,deck,canonical)
    if 'body_spacing' in design: data['body_spacing']=design['body_spacing']
    if 'enforce_body_mode' in design: data['enforce_body_mode']=design['enforce_body_mode']
    data['reference_hash']=hashlib.sha256((Path(project)/design['reference_image']).read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def check_body_policy(deck):
    design=deck.get('body_design',{})
    spacing=design.get('body_spacing')
    if spacing is not None:
        require(isinstance(spacing,dict),'Invalid body_spacing')
        y=spacing.get('start_y'); tolerance=spacing.get('tolerance',0.1)
        require(all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (y,tolerance)), 'Invalid body spacing numbers')
        require(0<=y<deck['size'][1] and tolerance>=0 and y+tolerance<deck['size'][1], 'Body spacing outside canvas')
    strict=design.get('enforce_body_mode',False)
    require(isinstance(strict,bool),'Invalid enforce_body_mode')
    for slide in deck['slides']:
        require(slide.get('type','content') in ('content','cover','contents','section','closing'),'Unknown slide type: '+str(slide.get('type')))
        if strict:
            require('type' in slide and 'mode' in slide,'Explicit type and mode required')
        if slide.get('type','content')!='content': continue
        if strict and resolve_mode(deck,slide)=='full':
            require(slide.get('body_design_exception') is True and isinstance(slide.get('user_decision'),str) and bool(slide['user_decision'].strip()),'Full body page needs recorded explicit user decision')
        if strict and resolve_mode(deck,slide)=='layered':
            require(page_style(deck,slide).get('show_title',True),'Layered body title must be native and visible')
        if spacing and resolve_mode(deck,slide)=='layered':
            require('body_spacing' not in slide and 'body_spacing' not in slide.get('style',{}),'Body spacing cannot be overridden per slide')
            title=page_style(deck,slide)['title_box']
            require(y>=title[1]+title[3],'Body start must be below title box; check actual title edge in render')


def validate_design(project,deck,stage):
    check_body_policy(deck)
    design=deck.get('body_design')
    if design is None:return
    require(isinstance(design.get('locked'),bool),'body_design.locked must be boolean')
    if not design['locked']:
        require(stage != 'ready' or deck.get('status',{}).get('samples') != 'confirmed','Confirmed samples require a body design lock before final assembly')
        warnings.warn('Body design is not locked; draft/samples only')
        return
    require(deck.get('status',{}).get('samples')=='confirmed','Confirm samples before locking design')
    require(design.get('fingerprint')==design_fingerprint(project,deck),'Body design changed: review samples and relock')
    canonical=design_signature(project,deck,{'layout':design['layout'],'style':design.get('style',{})})
    for slide in deck['slides']:
        if slide.get('type','content')!='content':continue
        if resolve_mode(deck,slide)=='full':
            require(slide.get('body_design_exception') is True,'Full body page requires explicit body_design_exception acknowledgement')
            warnings.warn('Full body page is outside native layout lock: '+str(slide['id']))
            continue
        require(design_signature(project,deck,slide)==canonical,'Body layout differs from locked design: '+str(slide['id']))


def validate(project, stage='ready'):
    require(stage in ('draft', 'ready'), 'Invalid validation stage')
    project = Path(project)
    deck = json.loads((project / 'deck.json').read_text(encoding='utf-8'))
    width, height = deck['size']
    check_body_policy(deck)
    require(all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in (width, height)), 'Invalid slide size')
    require(bool(deck['slides']), 'No slides')
    ids = set()
    for slide in deck['slides']:
        require(slide['id'] not in ids, 'Duplicate slide id')
        ids.add(slide['id'])
        mode = resolve_mode(deck, slide)
        require(mode in ('full', 'layered'), 'Resolve auto mode before assembly')
        style = page_style(deck, slide)
        for key in ('background', 'color'):
            require(isinstance(style.get(key), str) and re.fullmatch(r'[0-9A-Fa-f]{6}', style[key]), f'Invalid {key}: use six hex digits without #')
        logo = page_logo(deck, slide)
        if mode == 'layered':
            require(isinstance(slide.get('title'), str), 'Layered slide requires a text title')
            require(isinstance(style.get('font'), str) and bool(style['font'].strip()), 'Font is required')
            for key, default in (('title_size', 30), ('page_size', 12)):
                value = style.get(key, default)
                require(isinstance(value, (int, float)) and math.isfinite(value) and value > 0, f'Invalid {key}')
            check_chrome(style, width, height)
            content = image_box(deck, slide, style)
            fixed = list(fixed_regions(deck, slide, style).values())
            if logo and style.get('show_logo', True):
                check_image(project / logo)
            for box in [content, *fixed]:
                check_box(box, width, height)
            if composition(style) == 'framed':
                require(all(not overlaps(content, box) for box in fixed), 'Content overlaps fixed element')
            require(all(not overlaps(a, b) for i, a in enumerate(fixed) for b in fixed[i+1:]), 'Fixed elements overlap each other')
            background = style.get('background_image')
            if background:
                require(isinstance(background, str), 'Invalid background_image')
                if stage == 'ready' or (project/background).exists(): check_image(project/background, [0,0,width,height])
        else:
            content = [0, 0, width, height]
        require(isinstance(slide.get('image'), str) and bool(slide['image'].strip()), 'Image path is required')
        if stage == 'ready' or (project / slide['image']).exists():
            check_image(project / slide['image'], content)
            if mode == 'layered' and style.get('content_surface') == 'transparent':
                with Image.open(project/slide['image']) as image:
                    alpha = image.convert('RGBA').getchannel('A').getextrema()
                    require(alpha[0] < 255 and alpha[1] > 0, 'Transparent surface requires real, nonempty alpha; white/checkerboard RGB is not transparency')
            if mode == 'layered' and composition(style) == 'framed' and style.get('content_surface') == 'matched' and style.get('background_image'):
                warnings.warn('Matched opaque content over a background image requires visual seam inspection')
        for overlay in slide.get('overlays', []):
            box = overlay['box']
            check_box(box, width, height)
            if mode == 'layered':
                require(all(not overlaps(box, fixed_box) for fixed_box in fixed), 'Overlay overlaps reserved fixed element')
                x, y, w, h = box
                cx, cy, cw, ch = content
                require(x >= cx - 1e-6 and y >= cy - 1e-6 and x + w <= cx + cw + 1e-6 and y + h <= cy + ch + 1e-6, 'Overlay outside content box')
            require(isinstance(overlay.get('image'), str) and bool(overlay['image'].strip()), 'Overlay image path is required')
            if stage == 'ready' or (project / overlay['image']).exists():
                check_image(project / overlay['image'])
    validate_design(project,deck,stage)
    return deck


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--stage', choices=('draft', 'ready'), default='ready')
    args = parser.parse_args()
    validate(args.project, args.stage)
    print('Draft configuration validation passed (future images may be missing)' if args.stage == 'draft' else 'Project validation passed')
