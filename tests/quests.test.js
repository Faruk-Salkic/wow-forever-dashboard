const test=require('node:test');
const assert=require('node:assert/strict');
const Q=require('../assets/quests-core.js');
const common={id:1,level:16,min_level:9,classes:[],changed_at:null};
test('shared quest rewards stay on home and class-only quests go to the right player',()=>{
  const shaman={...common,id:2,classes:['Shaman']};
  const hunter={...common,id:3,classes:['Hunter']};
  const items=[common,shaman,hunter];
  assert.deepEqual(Q.select(items,{Faruk:10,Mirza:10}),[common]);
  assert.deepEqual(Q.select(items,{Faruk:10,Mirza:10},'Faruk'),[shaman]);
  assert.deepEqual(Q.select(items,{Faruk:10,Mirza:10},'Mirza'),[hunter]);
  assert.deepEqual(Q.select(items,{Faruk:40,Mirza:40}),[]);
});
test('new in Forever is not automatically a new discovery today',()=>{
  assert.equal(Q.recent({...common,source_change:'new'}),false);
  assert.equal(Q.recent({...common,changed_at:new Date().toISOString()}),true);
  assert.equal(Q.recent({...common,changed_at:'2000-01-01T00:00:00Z'}),false);
});
test('future weapon quests stay visible even when a profile is still at default level one',()=>{
  const early={id:'early',players:['Mirza'],min_level:9,max_level:22,quest_gear:{}};
  const raptor={id:'raptor',players:['Mirza'],min_level:22,max_level:32,quest_gear:{}};
  const later={id:'later',players:['Mirza'],min_level:29,max_level:42,quest_gear:{}};
  const shaman={...raptor,id:'shaman',players:['Faruk']};
  const shared={...raptor,id:'shared',players:['Faruk','Mirza']};
  const generic={id:'tip',players:['Mirza'],min_level:30,max_level:60};
  const items=[later,raptor,early,shaman,shared,generic];
  assert.deepEqual(Q.classHints(items,{Mirza:1,Faruk:22},'Mirza').map(x=>x.id),['early','raptor','later']);
  assert.deepEqual(Q.classHints(items,{Mirza:22},'Mirza').map(x=>x.id),['raptor','later','early']);
  assert.deepEqual(Q.classHints(items,{Mirza:30},'Mirza').map(x=>x.id),['later','raptor','tip']);
});
