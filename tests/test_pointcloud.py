import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pointcloud import write_glb
import test_export as export_fixture


def decode(path):
    raw=path.read_bytes();magic,version,size=struct.unpack_from('<III',raw)
    assert magic==0x46546c67 and version==2 and size==len(raw)
    n,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
    doc=json.loads(raw[20:20+n]);return doc,raw[28+n:]


class ModelCloudTests(unittest.TestCase):
    def test_all_points_centers_colors_and_disconnected_glyphs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cloud.glb';n=2201
            points=[{'position':[800+i*.25,450+i*.125,500+i],
                'color':[(i%256)/255,((i*7)%256)/255,((i*13)%256)/255],'diameter':3} for i in range(n)]
            r=write_glb(path,points,[800,450,0]);d,b=decode(path)
            self.assertEqual(r['points'],n);self.assertFalse(r['subsampled'])
            views=d['bufferViews'];xyz=list(struct.iter_unpack('<3f',b[views[0]['byteOffset']:views[0]['byteOffset']+views[0]['byteLength']]))
            self.assertEqual(len(xyz),n*6)
            for i,p in enumerate(points):
                center=[sum(v[j] for v in xyz[i*6:i*6+6])/6*r['units']*s+o for j,s,o in zip(range(3),[1,-1,-1],[800,450,0])]
                for a,c in zip(center,p['position']):self.assertAlmostEqual(a,c,places=3)
            for j in range(3):
                self.assertEqual(d['accessors'][0]['min'][j],min(v[j] for v in xyz))
                self.assertEqual(d['accessors'][0]['max'][j],max(v[j] for v in xyz))
            v=views[3];image=Image.open(io.BytesIO(b[v['byteOffset']:v['byteOffset']+v['byteLength']]))
            raw_pixels=image.tobytes();pixels=[tuple(raw_pixels[i:i+3]) for i in range(0,n*3,3)]
            self.assertEqual(pixels,[tuple(round(c*255) for c in p['color']) for p in points])
            v=views[2];indices=[v[0] for v in struct.iter_unpack('<I',b[v['byteOffset']:v['byteOffset']+v['byteLength']])]
            self.assertEqual(len(indices),n*24)
            self.assertTrue(all(len({v//6 for v in indices[i:i+3]})==1 for i in range(0,len(indices),3)))


class FullExportTests(unittest.TestCase):
    setUp=export_fixture.ExportTests.setUp
    tearDown=export_fixture.ExportTests.tearDown
    cli=export_fixture.ExportTests.cli

    def test_default_exports_entire_cloud_and_original_native_ply(self):
        points=self.root/'text/points3D.txt'
        with points.open('a') as f:
            for i in range(4,2205):f.write(f'{i} .3 .2 6 12 34 56 .1 1 0 2 0 3 0\n')
        native=self.root/'native.ply';native.write_bytes(b'ply\nformat ascii 1.0\ncomment keep native metadata\nelement vertex 2204\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n'+b'0 0 5 12 34 56\n'*2204)
        source=self.root/'solution.json';s=json.loads(source.read_text());s['cloud_ply']=str(native);source.write_text(json.dumps(s))
        out=self.root/'full';r=self.cli('export','--solution',source,'--out',out)
        self.assertEqual(r.returncode,0,r.stderr)
        scene=json.loads((out/'scene.json').read_text());report=json.loads((out/'report.json').read_text())
        self.assertEqual(scene['cloud_renderer'],'model');self.assertEqual(len(scene['cloud_points']),2204)
        self.assertEqual(scene['cloud_model']['points'],2204);self.assertTrue(report['full_cloud_display'])
        self.assertEqual(native.read_bytes(),(out/'points.ply').read_bytes())
        self.assertTrue((out/'check_rgb.jsx').exists() and (out/'rgb_check.glb').exists())

    def test_truncated_native_ply_is_rejected_without_hanging(self):
        native=self.root/'bad.ply'
        source=self.root/'solution.json';s=json.loads(source.read_text());s['cloud_ply']=str(native);source.write_text(json.dumps(s))
        for i,content in enumerate([b'',b'ply\nformat ascii 1.0\n']):
            native.write_bytes(content)
            r=self.cli('export','--solution',source,'--out',self.root/f'bad{i}')
            self.assertNotEqual(r.returncode,0);self.assertIn('PLY',r.stderr)


if __name__=='__main__':unittest.main()
