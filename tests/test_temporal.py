"""Optional fallback invariants; base requirements may skip these tests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import temporal_solve as temporal

np = temporal.np


@unittest.skipIf(np is None or temporal.cv2 is None, "optional requirements-tracking.txt not installed")
class TemporalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="temporal 한글 ")
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_mask_xy_coordinates_exclusion_and_resolution(self):
        path = self.root/"mask.json"
        data = {"width": 90, "height": 60,
                "polygons": [[[4, 30], [20, 30], [20, 50], [4, 50]]],
                "exclude_polygons": [[[8, 35], [12, 35], [12, 45], [8, 45]]]}
        path.write_text(json.dumps(data), encoding="utf-8")
        mask = temporal.read_mask(path, 90, 60)
        self.assertEqual(mask[40, 5], 255)
        self.assertEqual(mask[10, 40], 0)
        self.assertEqual(mask[40, 10], 0)
        with self.assertRaisesRegex(ValueError, "never auto-scale"):
            temporal.read_mask(path, 180, 120)
        data["polygons"][0][0] = [90, 20]
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside prepared pixels"):
            temporal.read_mask(path, 90, 60)

    def test_png_mask_requires_binary_grayscale_pixels(self):
        path = self.root/"mask.png"
        Image.new("L", (90, 60), 255).save(path)
        self.assertTrue((temporal.read_mask(path, 90, 60) == 255).all())
        Image.new("L", (90, 60), 127).save(path)
        with self.assertRaisesRegex(ValueError, "only black 0 and white 255"):
            temporal.read_mask(path, 90, 60)
        Image.new("L", (90, 60), 0).save(path)
        with self.assertRaisesRegex(ValueError, "no pixels"):
            temporal.read_mask(path, 90, 60)

    def test_unicode_frame_decode_and_missing_frames_are_not_skipped(self):
        image_path = self.root/"테스트.png"
        Image.new("L", (32, 24), 91).save(image_path)
        self.assertTrue((temporal.read_gray(image_path, 32, 24) == 91).all())
        names = [f"f{i:06d}.png" for i in range(3)]
        for name in names:
            Image.new("L", (32, 24), 91).save(self.root/name)
        manifest = {"schema": "aftereffect-colmap.frames.v1", "width": 32, "height": 24,
                    "fps_num": 24, "fps_den": 1, "images_dir": ".",
                    "frames": [{"frame": i, "name": name, "time_seconds": time}
                               for i, (name, time) in enumerate(zip(names, ["0", "1/24", "1/12"]))]}
        path = self.root/"manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(temporal.prepared(path)[1], names)
        (self.root/names[1]).unlink()
        with self.assertRaisesRegex(ValueError, "no frame may be skipped"):
            temporal.prepared(path)

    def test_heldout_tracks_never_enter_feature_or_raw_match_transport(self):
        tracks = np.empty((7, 125, 2))
        tracks[:, :, 0] = np.arange(125)[None, :]+.5
        tracks[:, :, 1] = np.arange(7)[:, None]+.5
        train, heldout, train_ids, heldout_ids = temporal.split_tracks(tracks)
        self.assertEqual((train.shape, heldout.shape), ((7, 100, 2), (7, 25, 2)))
        self.assertFalse(set(train_ids) & set(heldout_ids))
        self.assertEqual(sorted([*train_ids, *heldout_ids]), list(range(125)))
        self.assertTrue(np.array_equal(train, tracks[:, train_ids]))
        self.assertTrue(np.array_equal(heldout, tracks[:, heldout_ids]))
        names = [f"f{i:06d}.png" for i in range(7)]
        temporal.feature_files(self.root/"features", names, train)
        lines = (self.root/"features"/(names[0]+".txt")).read_text(encoding="utf-8").splitlines()
        imported_x = {float(line.split()[0]) for line in lines[1:]}
        self.assertEqual(imported_x, set(train[0, :, 0]))
        self.assertFalse(imported_x & set(heldout[0, :, 0]))
        self.assertTrue(all(len(line.split()) == 132 for line in lines[1:]))
        temporal.raw_matches(self.root/"raw.txt", names, 100)
        raw = (self.root/"raw.txt").read_text(encoding="utf-8")
        self.assertIn(names[0]+" "+names[-1]+"\n", raw)
        indices = [tuple(map(int, line.split())) for line in raw.splitlines() if line and not line.startswith("f")]
        self.assertTrue(all(a == b and 0 <= a < 100 for a, b in indices))

    def test_calibration_uses_prepared_pixels_and_cannot_refine(self):
        k = temporal.intrinsics(820, 460, 955)
        self.assertTrue(np.array_equal(k, [[955, 0, 410], [0, 955, 230], [0, 0, 1]]))
        cameras = {1: {"model": "SIMPLE_PINHOLE", "width": 820, "height": 460, "params": [955, 410, 230]}}
        images = {"a": {"camera_id": 1}, "b": {"camera_id": 1}}
        temporal.check_calibration(cameras, images, ["a", "b"], 820, 460, 955)
        cameras[1]["params"][0] += 1
        with self.assertRaisesRegex(ValueError, "intrinsics changed"):
            temporal.check_calibration(cameras, images, ["a", "b"], 820, 460, 955)
        for focal in (0, -1, float("nan"), float("inf")):
            with self.assertRaisesRegex(ValueError, "positive finite"):
                temporal.intrinsics(820, 460, focal)

    def test_native_cli_aliases_cover_colmap_312_and_42(self):
        aliases = ("Mapper.ba_local_min_tri_angle", "Mapper.local_ba_min_tri_angle")
        for name in aliases:
            self.assertEqual(temporal.option("  --"+name+" arg (=6)\n", *aliases), "--"+name)
        with self.assertRaisesRegex(ValueError, "Unsupported COLMAP CLI"):
            temporal.option("--Mapper.unrelated arg\n", *aliases)

    def projection_fixture(self, behind=0, count=3):
        k = temporal.intrinsics(640, 480, 600)
        rng = np.random.default_rng(42)
        xyz = rng.uniform([-1, -.8, 4], [1, .8, 8], (100, 3))
        xyz[:behind, 2] *= -1
        names = [f"frame{i}" for i in range(count)]
        images, observations = {}, []
        for i, name in enumerate(names):
            translation = np.array([-.25*i, 0, 0])
            images[name] = {"rotation": np.eye(3).tolist(), "translation": translation.tolist()}
            uv = (xyz+translation) @ k.T
            observations.append(uv[:, :2]/uv[:, 2:3])
        return np.asarray(observations), images, names, k

    def test_heldout_gate_accepts_image_fit_but_rejects_drift(self):
        observations, images, names, k = self.projection_fixture()
        report = temporal.heldout_report(observations, images, names, k)
        self.assertTrue(report["passed"])
        self.assertEqual(report["positive_depth_fraction"], 1)
        self.assertLess(report["p95_error_px"], 1e-8)
        observations[1, :, 0] += 5
        report = temporal.heldout_report(observations, images, names, k)
        self.assertFalse(report["passed"])
        self.assertGreater(report["p95_error_px"], 3)
        observations, images, names, k = self.projection_fixture(count=5)
        observations[1:-1, :, 0] += 2
        report = temporal.heldout_report(observations, images, names, k)
        self.assertGreater(report["median_error_px"], 1.5)
        self.assertLess(report["p95_error_px"], 3)
        self.assertFalse(report["passed"])

    def test_heldout_gate_rejects_negative_and_infinite_depth(self):
        observations, images, names, k = self.projection_fixture(behind=10)
        report = temporal.heldout_report(observations, images, names, k)
        self.assertLess(report["positive_depth_fraction"], .95)
        self.assertFalse(report["passed"])
        observations, images, names, k = self.projection_fixture()
        for image in images.values():
            image["translation"] = [0, 0, 0]
        observations[:] = observations[0]
        report = temporal.heldout_report(observations, images, names, k)
        self.assertFalse(report["finite"])
        self.assertFalse(report["passed"])
        json.dumps(report, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
