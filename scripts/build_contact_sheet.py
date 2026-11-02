import argparse,math
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
p=argparse.ArgumentParser();p.add_argument('--images',nargs='+',required=True);p.add_argument('--output',required=True);a=p.parse_args()
out=Path(a.output)
if out.exists():raise FileExistsError(out)
canvas=Image.new('RGB',(960,math.ceil(len(a.images)/3)*210),'white');draw=ImageDraw.Draw(canvas)
for i,path in enumerate(a.images):
    with Image.open(path) as im: thumb=ImageOps.contain(im.convert('RGB'),(310,180))
    x=(i%3)*320;y=(i//3)*210;canvas.paste(thumb,(x,y));draw.text((x,y+183),str(i+1),fill='black')
out.parent.mkdir(parents=True,exist_ok=True);canvas.save(out)
