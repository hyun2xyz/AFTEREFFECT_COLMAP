"""Generate an optional native AE projection check; no MCP or file-write setting.

Run it after importing the matching scene. AE's own toComp expression provides
the measured coordinates; the expected coordinates are projected in Python.
"""
import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from geometry import project


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scene",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    scene=json.loads(a.scene.read_text(encoding="utf-8"));samples=[]
    all_points=scene.get("cloud_points",scene["points"])
    selected=list(range(len(all_points)))
    if len(selected)>80:selected=[round(i*(len(selected)-1)/79) for i in range(80)]
    points=[all_points[i] for i in selected]
    model_cloud=scene.get('cloud_renderer')=='model';locals_by_id={}
    if model_cloud:
        raw=(a.scene.parent/scene['cloud_model']['file']).read_bytes();size=struct.unpack_from('<I',raw,12)[0]
        doc=json.loads(raw[20:20+size]);offset=20+size+8+doc['bufferViews'][0]['byteOffset']
        for i in selected:
            xyz=struct.unpack_from('<18f',raw,offset+i*72)
            locals_by_id[all_points[i]['id']]=[sum(xyz[j::3])/6*scene['cloud_model']['units']*s for j,s in enumerate([1,-1,-1])]
    indices=sorted({0,len(scene["frames"])//2,len(scene["frames"])-1})
    for index in indices:
        frame=scene["frames"][index]
        for point in points:
            expected=project(frame,point["xyz"],scene["intrinsics"])
            if expected is not None:samples.append({"id":point["id"],"time":index*scene["fps_den"]/scene["fps_num"],"expected":expected,"local":locals_by_id.get(point['id'])})
    data=json.dumps(samples,separators=(",",":"),allow_nan=False)
    jsx='''(function(){
var comp=app.project.activeItem;
if(!(comp instanceof CompItem) || !comp.layer("COLMAP_CAMERA"))throw new Error("Select matching COLMAP comp first");
var samples=__SAMPLES__,modelCloud=__MODEL_CLOUD__,errors=[],probe=null,version=app.version,problem=null,createdSource=null,before={};
for(var j=1;j<=app.project.numItems;j++)before[app.project.item(j).id]=true;
app.beginUndoGroup("Verify COLMAP camera projection");
try {
  probe=comp.layers.addNull();probe.name="TEMP_COLMAP_PROJECTION_CHECK";probe.enabled=false;
  createdSource=probe.source;
  var pos=probe.property("ADBE Transform Group").property("ADBE Position");
  for(var i=0;i<samples.length;i++){
    var s=samples[i],cloud=null;
    try{cloud=comp.layer("POINT_CLOUD_RGB");}catch(ignore){}
    if(cloud&&modelCloud){
      pos.expression='var pc=thisComp.layer("POINT_CLOUD_RGB");var f=100/pc.transform.scale[0];var p=['+s.local.join(',')+'];var v=pc.toComp([p[0]*f,p[1]*f,p[2]*f]);[v[0],v[1]];';
    }else if(cloud){
      if(!cloud.collapseTransformation)throw new Error("Cloud must preserve collapsed3D transformations");
      pos.expression='var pc=thisComp.layer("POINT_CLOUD_RGB");var v=pc.toComp(pc.source.layer("P_'+s.id+'").transform.position);[v[0],v[1]];';
    }else{
      if(!comp.layer("P_"+s.id))throw new Error("Missing point: "+s.id);
      pos.expression='var v=thisComp.layer("P_'+s.id+'").toComp([0,0,0]);[v[0],v[1]];';
    }
    var v=pos.valueAtTime(s.time,false);
    if(pos.expressionError)throw new Error(pos.expressionError);
    var dx=v[0]-s.expected[0],dy=v[1]-s.expected[1];errors.push(Math.sqrt(dx*dx+dy*dy));
  }
}catch(e){problem=e.toString();}finally{if(probe)probe.remove();if(createdSource&&!before[createdSource.id]&&createdSource.usedIn.length===0)createdSource.remove();app.endUndoGroup();}
errors.sort(function(a,b){return a-b;});
var max=errors[errors.length-1],p95=errors[Math.floor((errors.length-1)*0.95)];
var passed=!problem && errors.length===samples.length && isFinite(max) && max<0.5;
var result="COLMAP_QA_"+(passed?"PASS":"FAIL")+" | AE "+version+" | n="+errors.length+" | max="+(isFinite(max)?max.toFixed(6):"unknown")+" | p95="+(isFinite(p95)?p95.toFixed(6):"unknown");
if(problem)result+=" | "+problem;
comp.comment=result+"\\n"+comp.comment;comp.openInViewer();alert(result);
})();
'''.replace("__SAMPLES__",data).replace('__MODEL_CLOUD__','true' if model_cloud else 'false')
    a.out.write_text(jsx,encoding="utf-8")
    print(json.dumps({"jsx":str(a.out.resolve()),"samples":len(samples),"native_ae":"not_run"}))


if __name__=="__main__":main()
