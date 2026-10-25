/* Python-generated native AE point cloud. No MCP, plugins, save or close.
 * Point centers/RGB are measured; marker size is only a visible display choice.
 * Pose convention: B2AC a1e3c50 (MIT), see THIRD_PARTY_NOTICES.md. */
(function () {
  var d = /*__SCENE_DATA__*/;
  if (!d || !d.poses || !d.poses.length) throw new Error("Generate using colmap_ae.py export first");
  var first = new File(d.plates + "/" + d.firstPlate);
  if (!first.exists) throw new Error("Working plate missing: " + first.fsName);
  if (d.model && !(new File(d.model)).exists) throw new Error("Model file missing");
  if (!app.project) app.newProject();
  app.beginUndoGroup("COLMAP RGB cloud import");
  try {
    var tag="COLMAP_"+(new Date()).getTime(), duration=d.frameCount/d.fps;
    var folder=app.project.items.addFolder(tag), dataFolder=app.project.items.addFolder("_DATA");dataFolder.parentFolder=folder;
    var comp=app.project.items.addComp(tag+"_POINTCLOUD",d.width,d.height,1,duration,d.fps);comp.parentFolder=folder;comp.bgColor=[0,0,0];
    var black=comp.layers.addSolid([0,0,0],"BLACK_BACKGROUND",d.width,d.height,1,duration);black.source.parentFolder=dataFolder;black.locked=true;
    var io=new ImportOptions(first);io.sequence=true;io.forceAlphabetical=true;
    var plate=app.project.importFile(io);plate.parentFolder=dataFolder;plate.mainSource.conformFrameRate=d.fps;
    var bg=comp.layers.add(plate);bg.name="SOURCE_FOOTAGE (eye on for overlay)";bg.startTime=0;bg.enabled=false;bg.locked=true;
    var cloudData=app.project.items.addComp("POINT_DATA_"+d.points.length,d.width,d.height,1,duration,d.fps);cloudData.parentFolder=dataFolder;
    for(var n=0;n<d.points.length;n++){
      var p=d.points[n], layer=cloudData.layers.addShape();layer.name="P_"+p.id;layer.threeDLayer=true;layer.guideLayer=false;
      layer.autoOrient=AutoOrientType.CAMERA_OR_POINT_OF_INTEREST;
      var content=layer.property("ADBE Root Vectors Group"), circle=content.addProperty("ADBE Vector Shape - Ellipse");
      circle.property("ADBE Vector Ellipse Size").setValue([p.diameter,p.diameter]);
      var fill=content.addProperty("ADBE Vector Graphic - Fill");fill.property("ADBE Vector Fill Color").setValue(p.color);
      layer.property("ADBE Transform Group").property("ADBE Position").setValue(p.position);
    }
    var cloud=comp.layers.add(cloudData);cloud.name="POINT_CLOUD_RGB";cloud.threeDLayer=true;cloud.collapseTransformation=true;
    var ct=cloud.property("ADBE Transform Group");ct.property("ADBE Anchor Point").setValue([d.width/2,d.height/2,0]);ct.property("ADBE Position").setValue([d.width/2,d.height/2,0]);
    var cam=comp.layers.addCamera("COLMAP_CAMERA",[d.width/2,d.height/2]);cam.autoOrient=AutoOrientType.CAMERA_OR_POINT_OF_INTEREST;
    var tr=cam.property("ADBE Transform Group"),pos=tr.property("ADBE Position"),poi=tr.property("ADBE Anchor Point"),roll=tr.property("ADBE Rotate Z");
    for(var i=0;i<d.poses.length;i++){
      var t=d.poses[i].frame/d.fps;pos.setValueAtTime(t,d.poses[i].position);poi.setValueAtTime(t,d.poses[i].poi);roll.setValueAtTime(t,d.poses[i].roll);
    }
    cam.property("ADBE Camera Options Group").property("ADBE Camera Zoom").setValue(d.zoom);
    for(var p=0;p<3;p++){var prop=[pos,poi,roll][p];for(var j=1;j<=prop.numKeys;j++)prop.setInterpolationTypeAtKey(j,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);}
    if(d.plane||d.model){
      var origin=comp.layers.addNull();origin.name="WORLD_ORIGIN";origin.threeDLayer=true;origin.property("ADBE Transform Group").property("ADBE Position").setValue(d.origin);
    }
    if(d.plane){
      var guide=comp.layers.addSolid([.2,.65,.8],d.plane.toUpperCase()+"_GUIDE",1000,1000,1,duration);guide.source.parentFolder=dataFolder;guide.threeDLayer=true;guide.guideLayer=true;
      var gt=guide.property("ADBE Transform Group");gt.property("ADBE Position").setValue(d.origin);if(d.plane==="floor")gt.property("ADBE Rotate X").setValue(90);gt.property("ADBE Opacity").setValue(20);
    }
    if(d.model){
      var model=app.project.importFile(new ImportOptions(new File(d.model)));model.parentFolder=dataFolder;
      var ml=comp.layers.add(model);ml.name="USER_MODEL";ml.threeDLayer=true;
      ml.property("ADBE Transform Group").property("ADBE Position").setValue(d.origin);ml.property("ADBE Transform Group").property("ADBE Scale").setValue([d.modelScale,d.modelScale,d.modelScale]);
    }
    comp.comment="Measured sparse RGB cloud: "+d.points.length+" display markers. Source footage eye OFF; enable for overlay. Double-click cloud to edit points; keep Collapse Transformations enabled. Metric scale unverified.";
    comp.time=0;var viewer=comp.openInViewer();if(viewer)viewer.setActive();
  }finally{app.endUndoGroup();}
})();
