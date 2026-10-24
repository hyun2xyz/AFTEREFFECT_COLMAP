"""Opt-in real CPU COLMAP smoke on generated, redistributable textured planes.

Not part of unit tests: requires COLMAP, FFmpeg and Pillow. No downloaded assets.
Run via scripts/jobs.py, keeping the requested output directory and logs.
"""
import argparse
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from colmap_ae import binary
from geometry import cross, dot, mv, sub, unit


def linear_solve(rows, values):
    matrix=[list(map(float,row))+[float(v)] for row,v in zip(rows,values)]
    for col in range(len(values)):
        pivot=max(range(col,len(values)),key=lambda r:abs(matrix[r][col]))
        matrix[col],matrix[pivot]=matrix[pivot],matrix[col]
        denominator=matrix[col][col]
        if abs(denominator)<1e-12:raise ValueError("Degenerate synthetic homography")
        matrix[col]=[v/denominator for v in matrix[col]]
        for row in range(len(values)):
            if row==col:continue
            factor=matrix[row][col]
            matrix[row]=[v-factor*w for v,w in zip(matrix[row],matrix[col])]
    return [row[-1] for row in matrix]


def homography(quad, size):
    rows=[];values=[]
    for (u,v),(x,y) in zip(quad,[(0,0),(size-1,0),(size-1,size-1),(0,size-1)]):
        rows.extend([[u,v,1,0,0,0,-x*u,-x*v],[0,0,0,u,v,1,-y*u,-y*v]])
        values.extend([x,y])
    return linear_solve(rows,values)


def main():
    from PIL import Image,ImageDraw
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    images=out/"synthetic";images.mkdir();rng=random.Random(42);patches=[]
    for row in range(4):
        for col in range(5):
            depth=[4.0,6.0,8.0][(row*5+col)%3]
            u,v=85+col*115,70+row*110
            texture=Image.frombytes("RGB",(40,40),rng.randbytes(40*40*3)).resize((90,90))
            draw=ImageDraw.Draw(texture)
            for i in range(8):
                x=rng.randint(2,75);y=rng.randint(2,75)
                draw.rectangle((x,y,x+10,y+10),outline=(255,255,255),width=2)
            cx=(u-320)*depth/600;cy=(v-240)*depth/600;half=45*depth/600
            corners=[[cx-half,cy-half,depth],[cx+half,cy-half,depth],[cx+half,cy+half,depth],[cx-half,cy+half,depth]]
            patches.append((depth,corners,texture.convert("RGBA")))
    for index in range(12):
        image=Image.new("RGB",(640,480),(12,14,18))
        center=[(index-5.5)*.12,.025*math.sin(index*.4),.08*math.cos(index*.3)]
        forward=unit(sub([0,0,6],center));right=unit(cross([0,1,0],forward));down=cross(forward,right)
        rotation=[right,down,forward]
        for depth,corners,texture in sorted(patches,reverse=True,key=lambda q:q[0]):
            projected=[]
            for corner in corners:
                v=mv(rotation,sub(corner,center));projected.append((320+600*v[0]/v[2],240+600*v[1]/v[2]))
            x0=math.floor(min(p[0] for p in projected))-1;y0=math.floor(min(p[1] for p in projected))-1
            x1=math.ceil(max(p[0] for p in projected))+1;y1=math.ceil(max(p[1] for p in projected))+1
            local=[(x-x0,y-y0) for x,y in projected]
            tile=texture.transform((x1-x0,y1-y0),Image.Transform.PERSPECTIVE,homography(local,90),
                resample=Image.Resampling.BICUBIC,fillcolor=(0,0,0,0))
            image.paste(tile,(x0,y0),tile)
        image.save(images/f"f{index:06d}.png")
    video=out/"synthetic.mp4"
    subprocess.run([binary("ffmpeg"),"-nostdin","-v","error","-n","-framerate","24","-i",str(images/"f%06d.png"),
                    "-c:v","libx264","-crf","12","-pix_fmt","yuv420p",str(video)],check=True)
    cli=[sys.executable,"-B",str(ROOT/"scripts"/"colmap_ae.py")]
    started=time.monotonic()
    for args in (["prepare","--video",str(video),"--out",str(out/"prepared"),"--max-size","640"],
                 ["solve","--input",str(out/"prepared"),"--out",str(out/"solve"),"--threads","2"],
                 ["export","--solution",str(out/"solve"/"solution.json"),"--out",str(out/"export")]):
        subprocess.run(cli+args,check=True)
    report=json.loads((out/"export"/"report.json").read_text())
    assert report["frames"]==12 and report["missing_frames"]==0,report
    assert (out/"export"/"import_scene.jsx").is_file()
    print(json.dumps({"real_colmap_smoke":"passed","frames":12,"elapsed_seconds":round(time.monotonic()-started,2),
                      "median_point_error_px":report["median_colmap_point_error_px"],"native_AE":"not_run"}))


if __name__=="__main__":main()
