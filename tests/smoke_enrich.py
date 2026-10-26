"""Opt-in native known-camera triangulation + full RGB export on synthetic data."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from colmap_ae import fresh,load,save
from geometry import read_model


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--solution',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();source=load(a.solution);manifest=load(source['manifest'])
    if len(manifest['frames'])!=12 or Path(manifest['source']).name!='synthetic.mp4':
        raise ValueError('Use only the generated12-frame smoke fixture')
    out=fresh(a.out)
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/enrich_cloud.py'),'--solution',str(a.solution.resolve()),
        '--out',str(out/'solve'),'--threads','2'],check=True)
    result=load(out/'solve/solution.json')
    assert result['ready_for_export'] and result['registered']==12 and result['points']>=100,result
    assert result['camera_pose_max_absolute_delta']<=1e-8,result
    assert result['cloud_method']=='native_point_triangulator'
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/colmap_ae.py'),'export','--solution',str(out/'solve/solution.json'),
        '--out',str(out/'export')],check=True)
    scene=load(out/'export/scene.json');report=load(out/'export/report.json')
    _,_,points=read_model(result['text_model'])
    assert len(scene['cloud_points'])==scene['total_points']==len(points)==report['display_cloud_points']
    assert report['full_cloud_display'] and scene['cloud_renderer']=='model'
    assert (out/'export/points.ply').read_bytes()==Path(result['cloud_ply']).read_bytes()
    raw=(out/'export/pointcloud.glb').read_bytes();length=struct.unpack_from('<I',raw,12)[0]
    gltf=json.loads(raw[20:20+length]);assert gltf['accessors'][0]['count']==6*len(points)
    report={'native_enrich_smoke':'passed','frames':12,'points':len(points),
        'camera_pose_delta':result['camera_pose_max_absolute_delta'],'display_sampling':False,
        'native_ply_copy_exact':True,'native_AE':'not_run'}
    save(out/'smoke-report.json',report);print(json.dumps(report))


if __name__=='__main__':main()
