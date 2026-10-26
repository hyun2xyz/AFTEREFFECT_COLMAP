import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from geometry import cloud_glyphs,world_position
from test_geometry import fixture
import test_export as export_fixture


class CloudTests(unittest.TestCase):
    def test_far_points_keep_centers_and_rgb_while_becoming_visible(self):
        s=fixture();s["points"]=[{"id":7,"xyz":[10,20,1000000],"rgb":[13,101,255]}]
        p=cloud_glyphs(s)[0];k=s["intrinsics"];distance=1000000*s["world"]["scale"]
        self.assertEqual(p["position"],world_position(s["points"][0]["xyz"],s["world"],k))
        self.assertEqual(p["color"],[13/255,101/255,1])
        self.assertLess(5*k["fx"]/distance,1)
        self.assertAlmostEqual(p["diameter"]*k["fx"]/distance,6)
        s["point_size_px"]=0
        with self.assertRaises(ValueError):cloud_glyphs(s)


class CloudExportTests(unittest.TestCase):
    setUp=export_fixture.ExportTests.setUp
    tearDown=export_fixture.ExportTests.tearDown
    cli=export_fixture.ExportTests.cli
    def test_ply_keeps_entire_cloud_when_display_is_limited(self):
        p=self.root/"text/points3D.txt"
        with p.open("a") as stream:
            stream.write("4 .3 .2 6 12 34 56 .1 1 0 2 0 3 0\n5 .4 .1 6 67 89 10 .1 1 0 2 0 3 0\n")
        out=self.root/"cloud";r=self.cli("export","--solution",self.root/"solution.json","--out",out,"--cloud-renderer","shapes","--cloud-limit","3")
        self.assertEqual(r.returncode,0,r.stderr)
        s=json.loads((out/"scene.json").read_text());self.assertEqual(len(s["cloud_points"]),3)
        ply=(out/"points.ply").read_text();self.assertIn("element vertex 5\n",ply)
        rows=ply.split("end_header\n")[1].splitlines();self.assertEqual(len(rows),5)
        self.assertEqual(list(map(int,rows[3].split()[3:])),[12,34,56])

    def test_failed_temporal_report_blocks_export_before_reading_model(self):
        path=self.root/"heldout.json";path.write_text(json.dumps({"passed":False,"finite":True,"median_error_px":.1,"p95_error_px":.2,"positive_depth_fraction":1}))
        p=self.root/"solution.json";s=json.loads(p.read_text());s.update(method="temporal_lk",heldout_passed=False,ready_for_export=True,heldout_report=str(path));p.write_text(json.dumps(s))
        out=self.root/"blocked";r=self.cli("export","--solution",p,"--out",out)
        self.assertNotEqual(r.returncode,0);self.assertIn("heldout",r.stderr);self.assertFalse(out.exists())


if __name__=="__main__":unittest.main()
