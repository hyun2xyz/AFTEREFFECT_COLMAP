"""Generate an optional native AE projection check; no MCP or file-write setting.

Run it after importing the matching scene. AE's own toComp expression provides
the measured coordinates; the expected coordinates are projected in Python.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from geometry import project


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scene",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    scene=json.loads(a.scene.read_text(encoding="utf-8"));samples=[]
    indices=sorted({0,len(scene["frames"])//2,len(scene["frames"])-1})
    for index in indices:
        frame=scene["frames"][index]
        for point in scene["points"]:
            expected=project(frame,point["xyz"],scene["intrinsics"])
            if expected is not None:samples.append({"id":point["id"],"time":index*scene["fps_den"]/scene["fps_num"],"expected":expected})
    data=json.dumps(samples,separators=(",",":"),allow_nan=False)
    jsx='''(function(){
var comp=app.project.activeItem;
if(!(comp instanceof CompItem) || !comp.layer("COLMAP_CAMERA"))throw new Error("Select matching COLMAP comp first");
var samples=__SAMPLES__, errors=[],probe=null,version=app.version,problem=null;
app.beginUndoGroup("Verify COLMAP camera projection");
try {
  probe=comp.layers.addNull();probe.name="TEMP_COLMAP_PROJECTION_CHECK";probe.enabled=false;
  var pos=probe.property("ADBE Transform Group").property("ADBE Position");
  for(var i=0;i<samples.length;i++){
    var s=samples[i];if(!comp.layer("P_"+s.id))throw new Error("Missing point: "+s.id);
    pos.expression='var v=thisComp.layer("P_'+s.id+'").toComp([0,0,0]);[v[0],v[1]];';
    var v=pos.valueAtTime(s.time,false);
    if(pos.expressionError)throw new Error(pos.expressionError);
    var dx=v[0]-s.expected[0],dy=v[1]-s.expected[1];errors.push(Math.sqrt(dx*dx+dy*dy));
  }
}catch(e){problem=e.toString();}finally{if(probe)probe.remove();app.endUndoGroup();}
errors.sort(function(a,b){return a-b;});
var max=errors[errors.length-1],p95=errors[Math.floor((errors.length-1)*0.95)];
var passed=!problem && errors.length===samples.length && isFinite(max) && max<0.5;
var result="COLMAP_QA_"+(passed?"PASS":"FAIL")+" | AE "+version+" | n="+errors.length+" | max="+(isFinite(max)?max.toFixed(6):"unknown")+" | p95="+(isFinite(p95)?p95.toFixed(6):"unknown");
if(problem)result+=" | "+problem;
var label=comp.layers.addText(result);label.name=result;label.guideLayer=true;label.comment=result;
label.property("ADBE Transform Group").property("ADBE Position").setValue([20,30]);
comp.comment=result;comp.openInViewer();
})();
'''.replace("__SAMPLES__",data)
    a.out.write_text(jsx,encoding="utf-8")
    print(json.dumps({"jsx":str(a.out.resolve()),"samples":len(samples),"native_ae":"not_run"}))


if __name__=="__main__":main()
