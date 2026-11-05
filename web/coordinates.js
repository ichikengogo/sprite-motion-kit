'use strict';
const SpriteCoordinates={
 placement(original,width,height,space){
  if(space==='normalized'&&width===384&&height===384)return [0,0,384,384];
  if(space==='source'&&original&&width===original.width&&height===original.height){
   const n=original.normalization;
   if(!n||![n.x,n.y,n.scale].every(Number.isFinite)||n.scale<=0)throw Error('不正な正規化情報');
   return [n.x,n.y,width*n.scale,height*n.scale];
  }
  throw Error('補充座標を選んでください。元画像座標は元と同寸法、正規化座標は384x384が必要です。トリミングは禁止です。');
 },
 mayConfirm(part){return part.availability!=='missing';}
};
if(typeof module!=='undefined')module.exports=SpriteCoordinates;
