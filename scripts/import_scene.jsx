/* Python-generated scene. Review before running. Requires licensed After Effects.
 * Creates a NEW comp/folder; initializes a project only if none exists. Never saves/closes it.
 * Sparse RGB guide shapes are not a dense point-cloud renderer.
 * Pose convention: B2AC a1e3c50 (MIT), see THIRD_PARTY_NOTICES.md. */
(function () {
  var d = /*__SCENE_DATA__*/;
  if (!d || !d.poses || !d.poses.length) throw new Error("Generate this file using colmap_ae.py export first");
  if (!app.project) app.newProject();
  var first = new File(d.plates + "/" + d.firstPlate);
  if (!first.exists) throw new Error("Working plate missing: " + first.fsName);
  if (d.model && !(new File(d.model)).exists) throw new Error("Model file missing");
  app.beginUndoGroup("COLMAP teaching import");
  try {
    var tag = "COLMAP_" + (new Date()).getTime();
    var folder = app.project.items.addFolder(tag);
    var comp = app.project.items.addComp(tag, d.width, d.height, 1, d.frameCount / d.fps, d.fps);
    comp.parentFolder = folder;
    var io = new ImportOptions(first); io.sequence = true; io.forceAlphabetical = true;
    var plate = app.project.importFile(io); plate.parentFolder = folder;
    plate.mainSource.conformFrameRate = d.fps;
    var bg = comp.layers.add(plate); bg.name = "UNDISTORTED_CENTERED_PLATE";
    bg.startTime = 0; bg.locked = true;
    var cam = comp.layers.addCamera("COLMAP_CAMERA", [d.width/2, d.height/2]);
    cam.autoOrient = AutoOrientType.CAMERA_OR_POINT_OF_INTEREST;
    var tr = cam.property("ADBE Transform Group");
    var pos = tr.property("ADBE Position"), poi = tr.property("ADBE Anchor Point"), roll = tr.property("ADBE Rotate Z");
    for (var i=0; i<d.poses.length; i++) {
      var t = d.poses[i].frame / d.fps;
      pos.setValueAtTime(t, d.poses[i].position);
      poi.setValueAtTime(t, d.poses[i].poi);
      roll.setValueAtTime(t, d.poses[i].roll);
    }
    cam.property("ADBE Camera Options Group").property("ADBE Camera Zoom").setValue(d.zoom);
    // Every source frame must be measured. HOLD makes no smooth inferred poses between frames.
    for(var p=0; p<3; p++) {
      var prop=[pos,poi,roll][p];
      for(var j=1; j<=prop.numKeys; j++) prop.setInterpolationTypeAtKey(j,KeyframeInterpolationType.HOLD,KeyframeInterpolationType.HOLD);
    }
    for (var n=0; n<d.points.length; n++) {
      var point = d.points[n], layer = comp.layers.addShape();
      layer.name = "P_"+point.id; layer.threeDLayer = true;
      var content = layer.property("ADBE Root Vectors Group");
      var circle = content.addProperty("ADBE Vector Shape - Ellipse");
      circle.property("ADBE Vector Ellipse Size").setValue([5,5]);
      var fill = content.addProperty("ADBE Vector Graphic - Fill");
      fill.property("ADBE Vector Fill Color").setValue(point.color);
      layer.property("ADBE Transform Group").property("ADBE Position").setValue(point.position);
      layer.guideLayer = true; layer.comment = "COLMAP RGB guide; disable/hide for delivery";
    }
    var origin = comp.layers.addNull(); origin.name = "WORLD_ORIGIN"; origin.threeDLayer = true;
    origin.property("ADBE Transform Group").property("ADBE Position").setValue(d.origin);
    if (d.plane) {
      var guide = comp.layers.addSolid([0.2,0.65,0.8],d.plane.toUpperCase()+"_GUIDE",1000,1000,1,comp.duration);
      guide.threeDLayer = true; guide.guideLayer = true;
      var gt=guide.property("ADBE Transform Group"); gt.property("ADBE Position").setValue(d.origin);
      if(d.plane === "floor") gt.property("ADBE Rotate X").setValue(90);
      gt.property("ADBE Opacity").setValue(20);
    }
    if (d.model) {
      var modelIO=new ImportOptions(new File(d.model)), model=app.project.importFile(modelIO);
      model.parentFolder=folder;
      var modelLayer=comp.layers.add(model); modelLayer.name="USER_MODEL"; modelLayer.threeDLayer=true;
      modelLayer.property("ADBE Transform Group").property("ADBE Position").setValue(d.origin);
      modelLayer.property("ADBE Transform Group").property("ADBE Scale").setValue([d.modelScale,d.modelScale,d.modelScale]);
      // Native model import selects Advanced 3D on supported AE versions.
    }
    comp.openInViewer();
  } finally { app.endUndoGroup(); }
})();
