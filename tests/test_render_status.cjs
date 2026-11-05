'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const app=fs.readFileSync(require('node:path').join(__dirname,'../web/app.js'),'utf8');
const source=app.slice(app.indexOf("$('generate').onclick="),app.indexOf("$('export').onclick="));
const controls={};
const meta={frames:[{}],action:'walk',fps:8,duration:1,quality:{maxReachErrorPx:0}};
const ctx={$:id=>(controls[id]??={}),generation:0,invalidate(){},request:async()=>({json:async()=>({sheet:'fixture',meta})}),image:async()=>({}),performance:{now:()=>0},playback:{configure(){},setPlaying(){}},playing:false,JSON};
vm.createContext(ctx);vm.runInContext(source,ctx);
(async()=>{await controls.generate.onclick();assert.ok(!controls.status.textContent.startsWith('生成停止'));assert.equal(controls.export.disabled,false);console.log('Projected render status without optional quality arrays passed');})().catch(e=>{console.error(e);process.exitCode=1});
