from pathlib import Path
from contextlib import closing
import sqlite3
import struct
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from enrich_cloud import pose_delta,same_pixels,seed_model


class EnrichTests(unittest.TestCase):
    def test_pose_gate_uses_rotation_translation_and_rejects_motion(self):
        image={'rotation':[[1,0,0],[0,1,0],[0,0,1]],'translation':[0,0,0]}
        self.assertEqual(pose_delta({'a':image},{'a':image}),0)
        changed={**image,'translation':[.001,0,0]}
        with self.assertRaisesRegex(ValueError,'moved'):pose_delta({'a':image},{'a':changed})
        with self.assertRaisesRegex(ValueError,'lost'):pose_delta({'a':image},{})

    def test_reuse_checks_actual_pixels_not_only_names_and_dimensions(self):
        with tempfile.TemporaryDirectory(prefix='enrich 한글 ') as tmp:
            a=Path(tmp)/'a';b=Path(tmp)/'b';a.mkdir();b.mkdir();name='f000000.png'
            Image.new('RGB',(50,40),(10,30,60)).save(a/name,compress_level=1)
            Image.new('RGB',(50,40),(10,30,60)).save(b/name,compress_level=9)
            same_pixels(a,b,[name])
            Image.new('RGB',(50,40),(11,30,60)).save(b/name)
            with self.assertRaisesRegex(ValueError,'image plane differs'):same_pixels(a,b,[name])

    def test_seed_maps_native_database_image_ids_and_does_not_copy_old_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();db=root/'db'
            (source/'images.txt').write_text('1 1 0 0 0 0 0 0 1 f000000.png\n4 5 9\n2 1 0 0 0 -.1 0 0 1 f000001.png\n4 5 9\n')
            with closing(sqlite3.connect(db)) as con:
                con.execute('CREATE TABLE cameras(camera_id INTEGER,model INTEGER,width INTEGER,height INTEGER,params BLOB)')
                con.execute('INSERT INTO cameras VALUES(4,2,50,40,?)',(struct.pack('<4d',60,25,20,0),))
                con.execute('CREATE TABLE images(image_id INTEGER,name TEXT,camera_id INTEGER)')
                con.executemany('INSERT INTO images VALUES(?,?,4)',[(41,'f000000.png'),(52,'f000001.png')])
                con.commit()
            seed_model(source,root/'seed',db,['f000000.png','f000001.png'],{'model':'SIMPLE_PINHOLE','width':50,'height':40,'params':[60,25,20]})
            lines=(root/'seed/images.txt').read_text().splitlines()
            self.assertEqual(lines[0].split()[0],'41');self.assertEqual(lines[2].split()[0],'52')
            self.assertEqual(lines[0].split()[8],'4');self.assertEqual(lines[1],'')
            self.assertEqual((root/'seed/points3D.txt').read_text(),'')


if __name__=='__main__':unittest.main()
