/* First-host visual check. No file/network permission, automatic save or render. */
(function(){
  var d=/*__SCENE_DATA__*/,root=new File($.fileName).parent.fsName,file=new File(root+"/rgb_check.glb");
  if(!file.exists||parseFloat(app.version)<24.1)throw new Error("Keep rgb_check.glb beside this script; AE24.1+ required");
  if(!app.project)app.newProject();
  /*__CLOUD_HELPER__*/
  app.beginUndoGroup("COLMAP first-host RGB check");
  try{
    var folder=app.project.items.addFolder("COLMAP_RGB_CHECK"),comp=app.project.items.addComp("COLMAP_RGB_CHECK",1600,900,1,1,24);comp.parentFolder=folder;
    var black=comp.layers.addSolid([0,0,0],"BLACK_BACKGROUND",1600,900,1,1);black.source.parentFolder=folder;
    addMeasuredCloud(comp,file,folder,d.cloud,[800,450,0]);
    var cam=comp.layers.addCamera("CHECK_CAMERA",[800,450]);cam.position.setValue([800,450,-1920]);cam.pointOfInterest.setValue([800,450,0]);cam.zoom.setValue(1920);
    for(var i=0;i<d.positions.length;i++){
      var p=d.positions[i],x=800+(p[0]-800)*1920/(1920+p[2]),y=450+(p[1]-450)*1920/(1920+p[2]);
      var ref=comp.layers.addShape();ref.name="REFERENCE_RGB_"+d.colors[i].join("_");
      var contents=ref.property("ADBE Root Vectors Group"),circle=contents.addProperty("ADBE Vector Shape - Ellipse");circle.property("ADBE Vector Ellipse Size").setValue([20,20]);
      var fill=contents.addProperty("ADBE Vector Graphic - Fill");fill.property("ADBE Vector Fill Color").setValue([d.colors[i][0]/255,d.colors[i][1]/255,d.colors[i][2]/255]);ref.position.setValue([x-35,y]);
    }
    var title=comp.layers.addText("Compare each pair: LEFT = reference RGB / RIGHT = 3D point.\nIf colors differ, inspect project color settings.");title.position.setValue([70,100]);
    var sourceText=title.property("ADBE Text Properties").property("ADBE Text Document"),text=sourceText.value;
    text.fontSize=24;text.applyFill=true;text.fillColor=[1,1,1];text.applyStroke=false;sourceText.setValue(text);
    comp.comment="First-host RGB/unit check. Compare all five pairs before declaring native color fidelity; Windows AE not pre-verified.";
    var v=comp.openInViewer();if(v)v.setActive();
  }finally{app.endUndoGroup();}
})();
