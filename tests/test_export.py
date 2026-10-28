import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/"scripts/colmap_ae.py"


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="colmap class 한글 ")
        self.root=Path(self.tmp.name);text=self.root/"text";text.mkdir();images=self.root/"images";images.mkdir()
        (text/"cameras.txt").write_text("1 PINHOLE 640 480 500 500 311.25 243.75\n", encoding="utf-8")
        lines=[]
        for i in range(3):
            name=f"f{i:06d}.png";Image.new("RGB",(640,480),(10+i,20,30)).save(images/name)
            lines.extend([f"{i+1} 1 0 0 0 {-i*.1} 0 0 1 {name}","0 0 1"])
        (text/"images.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
        (text/"points3D.txt").write_text("1 0 1 5 255 0 0 .1 1 0 2 0 3 0\n2 1 1 5 0 255 0 .2 1 0 2 0 3 0\n3 0 1 7 0 0 255 .3 1 0 2 0 3 0\n", encoding="utf-8")
        manifest={"fps_num":24,"fps_den":1,"frames":[{"frame":i,"name":f"f{i:06d}.png","time_seconds":["0","1/24","1/12"][i]} for i in range(3)]}
        (self.root/"manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.root/"solution.json").write_text(json.dumps({"manifest":str(self.root/"manifest.json"),"text_model":str(text),"images_dir":str(images)}), encoding="utf-8")

    def tearDown(self):self.tmp.cleanup()

    def cli(self,*args):
        return subprocess.run([sys.executable,"-B",str(CLI),*map(str,args)],capture_output=True,encoding="utf-8",timeout=20)

    def test_export_centered_plates_rgb_and_anchor(self):
        out=self.root/"export";r=self.cli("export","--solution",self.root/"solution.json","--out",out)
        self.assertEqual(r.returncode,0,r.stderr)
        scene=json.loads((out/"scene.json").read_text(encoding="utf-8"));report=json.loads((out/"report.json").read_text(encoding="utf-8"))
        self.assertEqual(len(scene["frames"]),3);self.assertEqual([p["rgb"] for p in scene["points"]],[[255,0,0],[0,255,0],[0,0,255]])
        self.assertEqual(scene["intrinsics"]["source_cx"],311.25)
        with Image.open(out/"plates/f000000.png") as image:
            self.assertEqual(image.size,(scene["intrinsics"]["width"],scene["intrinsics"]["height"]))
        self.assertEqual(report["ae_import"],"not_run");self.assertTrue((out/"review.jpg").is_file())
        anchored=self.root/"floor"
        r=self.cli("anchor","--scene",out/"scene.json","--points","1,2,3","--plane","floor","--out",anchored)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads((anchored/"scene.json").read_text(encoding="utf-8"))["world"]["plane"],"floor")
        r=self.cli("export","--solution",self.root/"solution.json","--out",out)
        self.assertNotEqual(r.returncode,0);self.assertTrue((out/"scene.json").is_file())

    def test_missing_frame_blocks_export_without_inventing_keys(self):
        p=self.root/"text/images.txt";p.write_text("\n".join(p.read_text(encoding="utf-8").splitlines()[:4])+"\n", encoding="utf-8")
        out=self.root/"blocked";r=self.cli("export","--solution",self.root/"solution.json","--out",out)
        self.assertNotEqual(r.returncode,0);self.assertIn("unregistered",r.stderr);self.assertFalse(out.exists())

    def test_anamorphic_camera_blocks_export(self):
        (self.root/"text/cameras.txt").write_text("1 PINHOLE 640 480 500 550 320 240\n", encoding="utf-8")
        r=self.cli("export","--solution",self.root/"solution.json","--out",self.root/"blocked")
        self.assertNotEqual(r.returncode,0);self.assertIn("non-square",r.stderr)


if __name__=="__main__":unittest.main()
