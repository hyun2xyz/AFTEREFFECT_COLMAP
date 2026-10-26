/* Python-generated full native RGB cloud. Adds a new folder/comp; never saves/closes. */
(function(){
  var d=/*__SCENE_DATA__*/;
  if(parseFloat(app.version)<24.1)throw new Error("Full model display needs AE24.1+ Advanced3D; use explicit shapes fallback for older AE");
  var root=new File($.fileName).parent.fsName,first=new File(root+"/plates/"+d.firstPlate);
  if(!first.exists)first=new File(d.plates+"/"+d.firstPlate);
  var cloudFile=new File(root+"/"+d.cloud.file);
  if(!first.exists||!cloudFile.exists)throw new Error("Keep pointcloud.glb and plates beside the importer");
  if(d.model&&!(new File(d.model)).exists)throw new Error("User model missing");
  if(!app.project)app.newProject();
  /*__CLOUD_HELPER__*/
  app.beginUndoGroup("Import complete COLMAP RGB cloud");
  try{
    var tag="COLMAP_"+(new Date()).getTime(),duration=d.frameCount/d.fps;
    var folder=app.project.items.addFolder(tag),data=app.project.items.addFolder("_DATA");data.parentFolder=folder;
    var comp=app.project.items.addComp(tag+"_FULL_RGB",d.width,d.height,1,duration,d.fps);comp.parentFolder=folder;
    var black=comp.layers.addSolid([0,0,0],"BLACK_BACKGROUND",d.width,d.height,1,duration);black.source.parentFolder=data;black.locked=true;
    var io=new ImportOptions(first);io.sequence=true;io.forceAlphabetical=true;
    var plate=app.project.importFile(io);plate.parentFolder=data;plate.mainSource.conformFrameRate=d.fps;
    var bg=comp.layers.add(plate);bg.name="SOURCE_FOOTAGE (eye on for overlay)";bg.enabled=false;bg.locked=true;
    addMeasuredCloud(comp,cloudFile,data,d.cloud,d.origin);
    var cam=comp.layers.addCamera("COLMAP_CAMERA",[d.width/2,d.height/2]);cam.autoOrient=AutoOrientType.CAMERA_OR_POINT_OF_INTEREST;
    var ct=cam.property("ADBE Transform Group"),pos=ct.property("ADBE Position"),poi=ct.property("ADBE Anchor Point"),roll=ct.property("ADBE Rotate Z");
    for(var i=0;i<d.poses.length;i++){var t=d.poses[i].frame/d.fps;pos.setValueAtTime(t,d.poses[i].position);poi.setValueAtTime(t,d.poses[i].poi);roll.setValueAtTime(t,d.poses[i].roll);}
    cam.property("ADBE Camera Options Group").property("ADBE Camera Zoom").setValue(d.zoom);
    for(var p=0;p<3;p++){var prop=[pos,poi,roll][p];for(var j=1;j<=prop.numKeys;j++)prop.setInterpolationTypeAtKey(j,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);}
    if(d.plane||d.model){var origin=comp.layers.addNull();origin.name="WORLD_ORIGIN";origin.threeDLayer=true;origin.position.setValue(d.origin);}
    if(d.plane){var guide=comp.layers.addSolid([.2,.65,.8],d.plane.toUpperCase()+"_GUIDE",1000,1000,1,duration);guide.source.parentFolder=data;guide.threeDLayer=true;guide.guideLayer=true;guide.position.setValue(d.origin);if(d.plane==="floor")guide.xRotation.setValue(90);guide.opacity.setValue(20);}
    if(d.model){var asset=app.project.importFile(new ImportOptions(new File(d.model)));asset.parentFolder=data;var ml=comp.layers.add(asset);ml.name="USER_MODEL";ml.threeDLayer=true;ml.position.setValue(d.origin);ml.scale.setValue([d.modelScale,d.modelScale,d.modelScale]);}
    comp.comment="Complete native COLMAP RGB cloud: "+d.cloud.points+" points; no display sampling. SOURCE_FOOTAGE eye off; enable for overlay. Point glyphs are not surface geometry. Lens/metric depth unverified.";
    comp.time=0;var v=comp.openInViewer();if(v)v.setActive();
  }finally{app.endUndoGroup();}
})();
