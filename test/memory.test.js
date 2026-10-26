import test from 'node:test';
import assert from 'node:assert/strict';
import {ChatMemory} from '../public/memory.js';

test('close clears memory and prevents stale replies after reopening',()=>{
  const memory=new ChatMemory(); const first=memory.begin(); memory.remember(first,'Python SDK','Matching documentation.');
  const pending=memory.begin(); assert.equal(pending.history.length,2);
  memory.reset(false); assert.equal(pending.controller.signal.aborted,true); assert.throws(()=>memory.begin(),/closed/);
  memory.reset(true); assert.equal(memory.remember(pending,'old','late'),false); assert.deepEqual(memory.begin().history,[]);
});
test('sessions and copied histories stay isolated and bounded',()=>{
  const first=new ChatMemory(); const second=new ChatMemory();
  for(let i=0;i<10;i++){const request=first.begin();first.remember(request,'q'.repeat(2000),'a'.repeat(8000));}
  const request=first.begin(); assert.ok(request.history.length<=6); assert.ok(request.history.reduce((n,m)=>n+m.content.length,0)<=18000);
  request.history[0].content='changed'; assert.notEqual(first.history[0].content,'changed'); assert.deepEqual(second.begin().history,[]);
  first.reset(true); assert.deepEqual(first.begin().history,[]);
});
