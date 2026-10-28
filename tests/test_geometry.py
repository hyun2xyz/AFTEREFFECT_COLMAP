"""Independent numerical projection checks, not a native AE acceptance test."""
import copy
from fractions import Fraction
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from geometry import (ae_poses, centered_plate, cross, dot, mv, pinhole, plane_transform,
                      project, quaternion, read_model, sub, transpose, unit, world_position)
from colmap_ae import write_jsx


def fixture():
    return {"schema":"aftereffect-colmap.scene.v1", "intrinsics":{"width":640,"height":480,"fx":500,"fy":500,"cx":320,"cy":240},
        "fps_num":30000,"fps_den":1001,"plates":"/example/plates", "points":[],
        "world":{"origin":[0,0,0],"basis":[[1,0,0],[0,1,0],[0,0,1]],"scale":500},
        "frames":[{"frame":0,"name":"f000000.png","time_seconds":"0","rotation":[[1,0,0],[0,1,0],[0,0,1]],
                   "translation":[0,0,0],"center":[0,0,0]}]}


def ae_projection(pose, xyz, k):
    # Reconstruct the camera basis from AE POI and Z roll, independently of COLMAP R.
    f = unit(sub(pose["poi"], pose["position"]))
    r = unit(cross([0,1,0],f)); d = cross(f,r)
    angle = math.radians(pose["roll"])
    right = [math.cos(angle)*r[i]+math.sin(angle)*d[i] for i in range(3)]
    down = [-math.sin(angle)*r[i]+math.cos(angle)*d[i] for i in range(3)]
    v = sub(xyz, pose["position"]); z=dot(f,v)
    return [k["cx"]+k["fx"]*dot(right,v)/z, k["cy"]+k["fy"]*dot(down,v)/z]


class GeometryTests(unittest.TestCase):
    def test_quaternion_inverse_camera_center(self):
        r=quaternion([math.cos(.3),0,math.sin(.3),0]); t=[1,2,3]
        c=[-v for v in mv(transpose(r),t)]
        for v in [a+b for a,b in zip(mv(r,c),t)]: self.assertAlmostEqual(v,0)

    def test_ae_projection_matches_colmap_with_roll_and_aligned_floor(self):
        s=fixture()
        points=[{"id":1,"xyz":[-1,1,5]}, {"id":2,"xyz":[1,1,5]}, {"id":3,"xyz":[-1,1,8]}]
        transforms=[s["world"],plane_transform(points,[1,2,3],"floor",350)]
        for tr in transforms:
            s["world"]=tr
            for q in ([1,0,0,0], [math.cos(.21),0,0,math.sin(.21)], [math.cos(.13),0,math.sin(.13),0]):
                image=s["frames"][0];image["rotation"]=quaternion(q);image["translation"]=[-.2,.1,.3]
                image["center"]=[-v for v in mv(transpose(image["rotation"]),image["translation"])]
                pose=ae_poses(s)[0]
                for xyz in ([.1,.2,6],[-.3,.4,7],[1,-.2,8]):
                    expected=project(image,xyz,s["intrinsics"])
                    actual=ae_projection(pose,world_position(xyz,tr,s["intrinsics"]),s["intrinsics"])
                    for a,b in zip(expected,actual): self.assertAlmostEqual(a,b,places=8)

    def test_centered_plate_preserves_projection_with_real_translation(self):
        cam={"model":"PINHOLE","width":640,"height":480,"params":[500,500,311.25,243.75]}
        k=centered_plate(cam);s=fixture();frame=s["frames"][0]
        before=project(frame,[1,2,5],{"fx":500,"fy":500,"cx":311.25,"cy":243.75})
        after=project(frame,[1,2,5],k)
        self.assertAlmostEqual(before[0]+k["shift_x"],after[0]); self.assertAlmostEqual(before[1]+k["shift_y"],after[1])
        self.assertEqual(k["cx"],k["width"]/2)

    def test_lens_rejection_and_pole_rejection(self):
        for cam in ({"model":"SIMPLE_RADIAL","params":[500,320,240,.1]}, {"model":"PINHOLE","params":[500,510,320,240]}):
            with self.assertRaises(ValueError): pinhole(cam)
        s=fixture();s["frames"][0]["rotation"]=quaternion([math.sqrt(.5),math.sqrt(.5),0,0])
        with self.assertRaises(ValueError):ae_poses(s)

    def test_exact_zero_radial_is_pinhole_without_approximating_distortion(self):
        radial={"model":"SIMPLE_RADIAL","width":1600,"height":900,"params":[1920,800,450,0]}
        pin={"model":"PINHOLE","width":1600,"height":900,"params":[1920,1920,800,450]}
        self.assertEqual(centered_plate(radial),centered_plate(pin))
        k=centered_plate(radial)
        for x,y,z in ((1,2,5),(-3,.2,9),(0,0,1)):
            u,v=project(fixture()["frames"][0],[x,y,z],k)
            self.assertAlmostEqual(u,1920*x/z+800)
            self.assertAlmostEqual(v,1920*y/z+450)
        for distortion in (1e-12,-1e-12,.1,float("nan")):
            radial["params"][3]=distortion
            with self.assertRaises(ValueError):pinhole(radial)

    def test_floor_and_wall_are_coplanar_after_basis_change(self):
        pts=[{"id":1,"xyz":[2,1,3]},{"id":2,"xyz":[4,1,3]},{"id":3,"xyz":[2,1,6]}]
        k=fixture()["intrinsics"]
        for kind, axis, expected in (("floor",1,k["cy"]),("wall",2,0)):
            tr=plane_transform(pts,[1,2,3],kind,500,100)
            for p in pts:self.assertAlmostEqual(world_position(p["xyz"],tr,k)[axis],expected)
            self.assertAlmostEqual(tr["scale"],50)
        with self.assertRaises(ValueError):plane_transform(pts,[1,1,3],"floor",500)

    def test_text_reader_empty_observations_and_names_with_spaces(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"cameras.txt").write_text("# CAMERAS\n1 PINHOLE 640 480 500 500 320 240\n", encoding="utf-8")
            (p/"images.txt").write_text("# IMAGES\n1 1 0 0 0 0 0 0 1 image with spaces.png\n\n2 1 0 0 0 -1 0 0 1 next.png\n0 0 5\n", encoding="utf-8")
            (p/"points3D.txt").write_text("5 0 0 5 255 64 0 .1 1 0 2 0\n", encoding="utf-8")
            cams,images,points=read_model(p)
            self.assertEqual(images["next.png"]["center"],[1,0,0]);self.assertEqual(points[5]["rgb"],[255,64,0])
            self.assertIn("image with spaces.png",images)

    def test_jsx_rejects_missing_frames_and_non_cfr_time(self):
        s=fixture()
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"import.jsx"
            s["frames"][0]["frame"]=3
            with self.assertRaises(ValueError):write_jsx(s,out)
            s=fixture();s["frames"][0]["time_seconds"]="1/30"
            with self.assertRaises(ValueError):write_jsx(s,out)
            write_jsx(fixture(),out)
            text=out.read_text(encoding="utf-8")
            self.assertNotIn("/*__SCENE_DATA__*/",text)
            self.assertIn("KeyframeInterpolationType.HOLD",text)
            self.assertNotIn("app.project.save(",text)


if __name__=="__main__":unittest.main()
