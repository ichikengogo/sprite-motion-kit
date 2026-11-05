'use strict';
const assert=require('node:assert/strict'),{Clock}=require('../web/playback.js');
let checks=0;const eq=(a,b)=>{assert.equal(a,b);checks++;};
for(const refresh of [30,60,90,120,144]){
 const c=new Clock();c.configure(8,8,0);
 for(let i=0;i<=refresh*5;i++){const t=i*1000/refresh;eq(c.tick(t),Math.floor((t+1e-7)/125)%8);}
 eq(c.frame,0);
}
const c=new Clock();c.configure(8,8,0);eq(c.tick(124),0);eq(c.tick(125),1);eq(c.tick(999),7);eq(c.tick(1000),0);eq(c.tick(2625),5);
c.configure(8,8,3000);eq(c.setPlaying(false,3060),0);eq(c.tick(9000),0);eq(c.setPlaying(true,9000),0);eq(c.tick(9064),0);eq(c.tick(9065),1);
c.setPlaying(false,9100);c.seek(6,9200);eq(c.tick(12000),6);c.setPlaying(true,12000);eq(c.tick(12124),6);eq(c.tick(12125),7);eq(c.tick(12250),0);
c.configure(24/.64,24,13000);eq(c.tick(13640),0);eq(c.tick(13640+1000/(24/.64)),1);
c.configure(8,8,14000);eq(c.tick(14000),0);eq(c.tick(14001),0);
for(const args of [[0,8,0],[8,0,0],[NaN,8,0],[8,8,Infinity]]){assert.throws(()=>c.configure(...args));checks++;}
assert.throws(()=>c.seek(-1,0));checks++;assert.throws(()=>c.tick(NaN));checks++;
console.log(`${checks} elapsed playback assertions passed`);
