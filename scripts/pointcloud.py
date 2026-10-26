"""Whole measured RGB cloud as one native AE model; Pillow only, no sampling.

Each original point gets a small display glyph, not a connecting surface.
The complete source-coordinate PLY remains a separate output.
"""
from array import array
import argparse
import io
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent
UNITS = 512.0  # File normalization; importer measures the actual host's units.


def write_glb(path, glyphs, origin):
    from PIL import Image
    if not glyphs:
        raise ValueError("Cannot display an empty cloud")
    count = len(glyphs)
    if count*6 > 2**32-1:
        raise ValueError("Cloud exceeds GLB index capacity")
    positions, uvs, indices = array('f'), array('f'), array('I')
    palette = []
    directions = [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
    faces = [(0,2,4),(2,1,4),(1,3,4),(3,0,4),(2,0,5),(1,2,5),(3,1,5),(0,3,5)]
    width, height = 256, math.ceil(count/256)
    for i, p in enumerate(glyphs):
        if (len(p['position']) != 3 or len(p['color']) != 3 or
                not all(math.isfinite(v) for v in [*p['position'], *p['color'], p['diameter']]) or
                p['diameter'] <= 0 or any(v < 0 or v > 1 for v in p['color'])):
            raise ValueError("Invalid cloud center, RGB or display diameter")
        center = [(v-o)*s/UNITS for v,o,s in zip(p['position'], origin, [1,-1,-1])]
        radius = p['diameter']/(2*UNITS)
        try:
            for direction in directions:
                positions.extend(c+radius*d for c,d in zip(center,direction))
                uvs.extend(((i%width+.5)/width, (i//width+.5)/height))
        except OverflowError as exc:
            raise ValueError("Point exceeds GLB float range") from exc
        indices.extend(i*6+k for face in faces for k in face)
        palette.append(tuple(round(v*255) for v in p['color']))
    atlas = Image.new('RGB', (width,height))
    atlas.putdata(palette+[(0,0,0)]*(width*height-count))
    png = io.BytesIO(); atlas.save(png, format='PNG')
    lower = [min(positions[j::3]) for j in range(3)]
    upper = [max(positions[j::3]) for j in range(3)]
    binary = bytearray(); views = []
    def view(data, target=None):
        binary.extend(b'\0'*(-len(binary)%4)); offset = len(binary); binary.extend(data)
        result = {'buffer':0,'byteOffset':offset,'byteLength':len(data)}
        if target: result['target'] = target
        views.append(result); return len(views)-1
    def little(values):
        if sys.byteorder != 'little': values.byteswap()
        return values.tobytes()
    vp = view(little(positions),34962); vt = view(little(uvs),34962)
    vi = view(little(indices),34963); image_view = view(png.getvalue())
    data = {'asset':{'version':'2.0','generator':'COLMAP measured RGB point display'},
        'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0,'name':'COLMAP_RGB'}],
        'meshes':[{'primitives':[{'attributes':{'POSITION':0,'TEXCOORD_0':1},'indices':2,'material':0,'mode':4}]}],
        'materials':[{'doubleSided':True,'pbrMetallicRoughness':{'baseColorTexture':{'index':0},
            'metallicFactor':0,'roughnessFactor':1},'extensions':{'KHR_materials_unlit':{}}}],
        'extensionsUsed':['KHR_materials_unlit'],'extensionsRequired':['KHR_materials_unlit'],
        'textures':[{'sampler':0,'source':0}],
        'samplers':[{'magFilter':9728,'minFilter':9728,'wrapS':33071,'wrapT':33071}],
        'images':[{'bufferView':image_view,'mimeType':'image/png'}],
        'accessors':[{'bufferView':vp,'componentType':5126,'count':count*6,'type':'VEC3','min':lower,'max':upper},
            {'bufferView':vt,'componentType':5126,'count':count*6,'type':'VEC2'},
            {'bufferView':vi,'componentType':5125,'count':count*24,'type':'SCALAR'}],
        'bufferViews':views,'buffers':[{'byteLength':len(binary)}]}
    encoded = json.dumps(data,separators=(',',':'),allow_nan=False).encode('ascii')
    encoded += b' '*(-len(encoded)%4); binary.extend(b'\0'*(-len(binary)%4))
    with Path(path).open('xb') as stream:
        stream.write(struct.pack('<III',0x46546c67,2,28+len(encoded)+len(binary)))
        stream.write(struct.pack('<II',len(encoded),0x4e4f534a)); stream.write(encoded)
        stream.write(struct.pack('<II',len(binary),0x004e4942)); stream.write(binary)
    return {'points':count,'units':UNITS,'min':lower,'max':upper,'file':Path(path).name,
            'bytes':Path(path).stat().st_size,'subsampled':False}


def model_template(name):
    return (ROOT/name).read_text(encoding='utf-8').replace('/*__CLOUD_HELPER__*/',
        (ROOT/'cloud_model.jsxinc').read_text(encoding='utf-8'))


def write_rgb_check(out):
    positions = [[600,350,0],[1000,350,0],[600,650,0],[1000,650,200],[800,450,-200]]
    colors = [[32,64,128],[64,100,200],[180,100,45],[240,210,140],[120,128,136]]
    points = [{'position':pos,'color':[c/255 for c in rgb],'diameter':20} for pos,rgb in zip(positions,colors)]
    config = write_glb(out/'rgb_check.glb',points,[800,450,0])
    data = {'cloud':config,'positions':positions,'colors':colors}
    script = model_template('check_rgb.jsx').replace('/*__SCENE_DATA__*/',json.dumps(data,separators=(',',':')))
    (out/'check_rgb.jsx').write_text(script,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Make the small first-host AE RGB/unit check without a video, COLMAP or model weights')
    parser.add_argument('--rgb-check',action='store_true',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:
        out=args.out.expanduser().resolve();out.mkdir(parents=True,exist_ok=False);write_rgb_check(out)
        print(json.dumps({'jsx':str(out/'check_rgb.jsx'),'native_AE':'not_run'}))
    except (ValueError,OSError,ImportError) as exc:
        print(f'Error: {exc}',file=sys.stderr);raise SystemExit(1)
