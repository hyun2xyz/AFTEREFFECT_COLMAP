"""More native COLMAP RGB points with accepted cameras FIXED. Run via jobs.py.

Default: new CPU SIFT on accepted undistorted images. Reuse an existing SIFT DB
only when its declared source images are pixel-identical to these images.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import sqlite3
import struct
import subprocess
import sys

from colmap_ae import binary, capture, fresh, load, save, tool_env, validate_solution
from geometry import pinhole, read_model


def same_pixels(first, second, names):
    from PIL import Image
    for name in names:
        with Image.open(first/name) as a, Image.open(second/name) as b:
            if a.size != b.size or a.convert('RGB').tobytes() != b.convert('RGB').tobytes():
                raise ValueError(f"SIFT reuse image plane differs at {name}; omit --database to extract on accepted undistorted images")


def pose_delta(before, after):
    if set(before) != set(after):
        raise ValueError("Native triangulation lost or added camera frames")
    def values(image):
        return [*image['translation'],*(v for row in image['rotation'] for v in row)]
    delta = max(abs(a-b) for name in before for a,b in zip(values(before[name]),values(after[name])))
    if not math.isfinite(delta) or delta > 1e-8:
        raise ValueError(f"Accepted cameras moved ({delta}); output rejected")
    return delta


def option(help_text, *names):
    for name in names:
        if re.search(r'--'+re.escape(name)+r'\s',help_text):return '--'+name
    raise ValueError(f"Unsupported COLMAP options: {names}")


def seed_model(source, target, database, names, camera):
    fx,fy,cx,cy = pinhole(camera)
    with closing(sqlite3.connect(database)) as db:
        rows = list(db.execute('SELECT image_id,name,camera_id FROM images'))
        if {r[1] for r in rows} != set(names) or len(rows) != len(names):
            raise ValueError("SIFT database must contain exactly the accepted frame names")
        ids = {r[1]:r[0] for r in rows}; camera_ids = {r[2] for r in rows}
        if len(camera_ids) != 1:raise ValueError("Use a single shared SIFT camera")
        cid = camera_ids.pop()
        db.execute('UPDATE cameras SET model=0,width=?,height=?,params=? WHERE camera_id=?',
            (camera['width'],camera['height'],struct.pack('<3d',fx,cx,cy),cid))
        db.commit()
    target.mkdir()
    (target/'cameras.txt').write_text(f"{cid} SIMPLE_PINHOLE {camera['width']} {camera['height']} {fx:.17g} {cx:.17g} {cy:.17g}\n",encoding='ascii')
    lines = (source/'images.txt').read_text(encoding='utf-8').splitlines(); headers = {}; i = 0
    while i < len(lines):
        line = lines[i].strip(); i += 1
        if not line or line.startswith('#'):continue
        parts = line.split(maxsplit=9)
        if len(parts)!=10:raise ValueError("Malformed source pose")
        headers[parts[9]] = parts[1:8]; i += 1
    (target/'images.txt').write_text(''.join(' '.join([str(ids[name]),*headers[name],str(cid),name])+'\n\n' for name in names),encoding='utf-8')
    (target/'points3D.txt').write_text('',encoding='ascii')


def run(args):
    source_path = args.solution.expanduser().resolve(); source = load(source_path)
    validate_solution(source)
    if source.get('ready_for_export') is not True:
        raise ValueError("First accept a complete camera solution; enrichment cannot repair a failed camera solve")
    manifest = load(source['manifest']); names = [f['name'] for f in manifest['frames']]
    fps = Fraction(manifest['fps_num'],manifest['fps_den'])
    if (names != [f'f{i:06d}.png' for i in range(len(names))] or fps<=0 or
            any(f['frame']!=i or Fraction(f['time_seconds'])!=Fraction(i,1)/fps for i,f in enumerate(manifest['frames']))):
        raise ValueError("Use every prepared frame and exact CFR timing")
    cameras, accepted, _ = read_model(source['text_model'])
    if set(accepted) != set(names):raise ValueError("Camera model does not cover every prepared frame")
    used = {accepted[name]['camera_id'] for name in names}
    if len(used)!=1:raise ValueError("Starter needs one shared lens")
    camera = cameras[used.pop()]; fx,fy,cx,cy = pinhole(camera)
    images = Path(source['images_dir']).resolve()
    from PIL import Image
    for name in names:
        with Image.open(images/name) as im:
            if im.size != (camera['width'],camera['height']):raise ValueError("Accepted image size differs from camera")
    if bool(args.database) != bool(args.database_images):
        raise ValueError("Reuse requires both --database and --database-images; otherwise omit both")
    if args.database:same_pixels(args.database_images.expanduser().resolve(),images,names)
    angle = args.min_angle if args.min_angle is not None else source.get('min_angle_degrees',1.5)
    if not math.isfinite(angle) or not 0<angle<180:raise ValueError("Minimum angle must be finite,0..180 degrees")
    exe = binary('colmap',args.colmap); out = fresh(args.out); events = []
    solution = {**source,'ready_for_export':False,'cloud_method':'native_point_triangulator',
        'source_camera_solution':str(source_path),'camera_validation_inherited':True,
        'cloud_min_angle_degrees':angle,'cloud_reprojection_limit_px':3.0}
    save(out/'solution.json',solution)
    def step(stage, argv):
        event={'stage':stage,'started_at':datetime.now(timezone.utc).isoformat(),'command':[exe,*argv]}
        events.append(event);save(out/'stages.json',events)
        print(json.dumps({'stage':stage,'log':str(out/(stage+'.log'))}),flush=True)
        with (out/(stage+'.log')).open('x',encoding='utf-8') as log:
            result=subprocess.run([exe,*argv],stdout=log,stderr=subprocess.STDOUT,env=tool_env(exe))
        event.update(exit_code=result.returncode,ended_at=datetime.now(timezone.utc).isoformat());save(out/'stages.json',events)
        if result.returncode:raise ValueError(f"COLMAP {stage} failed; read {out/(stage+'.log')}")
    try:
        database=out/'database.db'
        if args.database:
            original=args.database.expanduser().resolve()
            with closing(sqlite3.connect(original.as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(database)) as dest:
                src.backup(dest);dest.commit()
        else:
            extraction=capture([exe,'feature_extractor','-h']);matching=capture([exe,'sequential_matcher','-h'])
            step('features',['feature_extractor','--database_path',str(database),'--image_path',str(images),
                '--ImageReader.single_camera','1','--ImageReader.camera_model','SIMPLE_PINHOLE',
                '--ImageReader.camera_params',f'{fx:.17g},{cx:.17g},{cy:.17g}',
                option(extraction,'FeatureExtraction.use_gpu','SiftExtraction.use_gpu'),'0',
                option(extraction,'FeatureExtraction.num_threads','SiftExtraction.num_threads'),str(args.threads)])
            step('matching',['sequential_matcher','--database_path',str(database),
                option(matching,'FeatureMatching.use_gpu','SiftMatching.use_gpu'),'0',
                option(matching,'FeatureMatching.num_threads','SiftMatching.num_threads'),str(args.threads),
                '--SequentialMatching.overlap',str(args.overlap)])
        seed=out/'fixed-cameras';seed_model(Path(source['text_model']),seed,database,names,camera)
        sparse=out/'sparse';sparse.mkdir()
        argv=['point_triangulator','--database_path',str(database),'--image_path',str(images),
            '--input_path',str(seed),'--output_path',str(sparse),'--clear_points','1','--refine_intrinsics','0',
            '--Mapper.num_threads',str(args.threads),'--Mapper.fix_existing_frames','1','--Mapper.extract_colors','1',
            '--Mapper.ba_refine_focal_length','0','--Mapper.ba_refine_principal_point','0','--Mapper.ba_refine_extra_params','0',
            '--Mapper.tri_min_angle',str(angle),'--Mapper.filter_min_tri_angle',str(angle),
            '--Mapper.filter_max_reproj_error','3','--Mapper.tri_merge_max_reproj_error','3','--Mapper.tri_complete_max_reproj_error','3']
        help_text=capture([exe,'point_triangulator','-h'])
        if '--Mapper.ba_refine_sensor_from_rig' in help_text:argv.extend(['--Mapper.ba_refine_sensor_from_rig','0'])
        step('triangulate',argv)
        text=out/'text';text.mkdir()
        step('text',['model_converter','--input_path',str(sparse),'--output_path',str(text),'--output_type','TXT'])
        new_cameras,new_images,points=read_model(text);delta=pose_delta(accepted,new_images)
        for name in names:
            new_camera=new_cameras[new_images[name]['camera_id']]
            if ((new_camera['width'],new_camera['height'])!=(camera['width'],camera['height']) or
                    any(not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10) for a,b in zip(pinhole(new_camera),[fx,fy,cx,cy]))):
                raise ValueError("Native triangulation changed the accepted lens")
        ply=out/'points.ply';step('ply',['model_converter','--input_path',str(sparse),'--output_path',str(ply),'--output_type','PLY'])
        solution.update(text_model=str(text),models={'fixed':len(new_images)},selected_model='fixed',
            registered=len(new_images),total_frames=len(names),missing_frames=[],points=len(points),
            cloud_ply=str(ply),camera_pose_max_absolute_delta=delta,ready_for_export=True,
            note='All native COLMAP RGB points with accepted cameras fixed. Existing lens/weak-depth assumptions remain; not dense stereo.')
        save(out/'solution.json',solution)
        print(json.dumps({'solution':str(out/'solution.json'),'points':len(points),'frames':len(names),'camera_pose_delta':delta}),flush=True)
    except Exception as exc:
        solution.update(ready_for_export=False,failure_reason=str(exc));save(out/'solution.json',solution);raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--solution',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--database',type=Path);p.add_argument('--database-images',type=Path)
    p.add_argument('--min-angle',type=float,help='inherit accepted temporal angle,otherwise1.5 degrees; never lower automatically')
    p.add_argument('--colmap');p.add_argument('--threads',type=int,choices=range(1,17),default=4)
    p.add_argument('--overlap',type=int,choices=range(2,31),default=8)
    try:run(p.parse_args())
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error,subprocess.SubprocessError) as exc:
        print(f'Error: {exc}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
