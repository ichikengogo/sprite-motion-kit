'use strict';
// Elapsed-time clock: refresh cadence must not change the clip's duration.
const SpritePlayback={Clock:class {
 constructor(){this.configure(24,24,0);this.playing=true;}
 configure(fps,count,now,frame=0){
  if(!Number.isFinite(fps)||fps<=0||!Number.isInteger(count)||count<1||!Number.isFinite(now))throw Error('Invalid playback metadata');
  this.fps=fps;this.count=count;this.last=now;this.carry=0;this.frame=0;this.seek(frame,now);
 }
 tick(now){
  if(!Number.isFinite(now))throw Error('Invalid playback time');
  const elapsed=Math.max(0,now-this.last);this.last=now;
  if(this.playing){
   this.carry+=elapsed;const interval=1000/this.fps,steps=Math.floor((this.carry+1e-9)/interval);
   if(steps){this.frame=(this.frame+steps)%this.count;this.carry=Math.max(0,this.carry-steps*interval);}
  }
  return this.frame;
 }
 setPlaying(value,now){this.tick(now);this.playing=!!value;this.last=now;return this.frame;}
 seek(frame,now){
  if(!Number.isInteger(frame)||frame<0||frame>=this.count||!Number.isFinite(now))throw Error('Invalid playback frame');
  this.frame=frame;this.carry=0;this.last=now;return frame;
 }
}};
if(typeof module!=='undefined')module.exports=SpritePlayback;
