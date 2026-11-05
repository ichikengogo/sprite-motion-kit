const assert=require('node:assert/strict');const c=require('../web/coordinates.js');
const original={width:384,height:384,normalization:{x:27,y:27,scale:330/384}};
assert.deepEqual(c.placement(original,384,384,'source'),[27,27,330,330]);
assert.deepEqual(c.placement(original,384,384,'normalized'),[0,0,384,384]);
assert.throws(()=>c.placement(original,120,120,'source'));
assert.throws(()=>c.placement(null,384,384,'source'));
assert.equal(c.mayConfirm({availability:'missing'}),false);
assert.equal(c.mayConfirm({availability:'unverified'}),true);
console.log('6 coordinate/missing-confirm assertions passed');
