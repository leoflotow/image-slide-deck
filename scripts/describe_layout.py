"""Read resolved geometry for image prompts; no separate safety-coordinate store."""
import argparse
import json
from pathlib import Path
from validate_project import page_style, resolve_mode, composition, image_box, fixed_regions, check_box


def describe(deck, slide):
    style=page_style(deck, slide)
    width,height=deck['size']
    box=image_box(deck,slide,style)
    regions=fixed_regions(deck,slide,style)
    for candidate in [box,*regions.values()]:check_box(candidate,width,height)
    result = {'id':slide['id'],'mode':resolve_mode(deck,slide),'composition':composition(style) if resolve_mode(deck,slide)=='layered' else None,'canvas_inches':[width,height],'image_box_inches':box,'image_aspect_ratio':box[2]/box[3],'reserved_regions':[{'role':role,'box_inches':b,'box_percent':[100*b[0]/width,100*b[1]/height,100*b[2]/width,100*b[3]/height]} for role,b in regions.items()],'design_reference':deck.get('body_design',{}).get('reference_image'),'design_locked':deck.get('body_design',{}).get('locked',False),'instruction':'Generate all planned body text and diagrams together. Keep body text and key diagrams out of reserved regions; background may continue through them. Do not leave full-width header/footer strips merely because local regions exist.'}
    spacing=deck.get('body_design',{}).get('body_spacing')
    if spacing and slide.get('type','content')=='content' and resolve_mode(deck,slide)=='layered':
        result['body_spacing']={**spacing,'tolerance':spacing.get('tolerance',0.1),'start_percent':100*spacing['start_y']/height}
        result['instruction'] += ' All meaningful body text and key diagrams must stay below body_spacing.start_y; the first meaningful group must begin within start_y plus tolerance. Background may flow across this boundary. Do not print the page title: '+slide.get('title','')
    separator=style.get('title_separator')
    if separator and resolve_mode(deck,slide)=='layered':
        result['title_separator']=separator
        result['body_min_y']=separator['box'][1]+separator.get('clearance',0.12)
        result['instruction'] += ' Do not draw the separator; it will be added natively. Body text and key diagrams must stay below body_min_y, but need not start at that boundary. Balance sparse content naturally within the available area; no fixed top gap or upward packing. Background continues through the whole slide.'
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',required=True)
    parser.add_argument('--slide-id',required=True)
    args=parser.parse_args()
    deck=json.loads((Path(args.project)/'deck.json').read_text(encoding='utf-8'))
    matches=[s for s in deck['slides'] if str(s['id'])==args.slide_id]
    if len(matches)!=1:parser.error('slide-id must identify exactly one slide')
    print(json.dumps(describe(deck,matches[0]),ensure_ascii=False,indent=2))
