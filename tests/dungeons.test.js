const test=require('node:test');
const assert=require('node:assert/strict');
const D=require('../assets/dungeons-core.js');
const storage=()=>{const values=new Map();return {getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v)};};
const quest={id:'dm_alba',progress_id:'dm_alba',game_id:92753,title:'Destruction in Deadmines',min_lvl:9,prepare_from_level:9,phase:'before',location_confirmed:true,classes:[]};
const data={dungeons:[{id:'dm',recommended_level:19,quests:[quest]}]};

test('early chain reminders use acceptance level rather than dungeon level',()=>{
  const rows=D.preparation(data,{Faruk:9,Mirza:9},storage());
  assert.equal(rows.length,1);assert.equal(rows[0].ready,true);
  assert.equal(D.visible(data,{Faruk:9,Mirza:9}).length,1);
  const late={dungeons:[{recommended_level:30,quests:[{...quest,min_lvl:20,prepare_from_level:20}]}]};
  assert.equal(D.preparation(late,{Faruk:1,Mirza:1},storage()).length,0);
  assert.equal(D.visible(late,{Faruk:1,Mirza:1}).length,0);
  assert.equal(D.visible(late,{Faruk:1,Mirza:1},true).length,1);
});

test('completion stays separate for each player and follows the actual quest across groups',()=>{
  const s=storage();s.setItem(D.storageKey('Faruk',quest),'1');
  assert.equal(D.done(quest,'Faruk',s),true);assert.equal(D.done(quest,'Mirza',s),false);
  assert.deepEqual(D.preparation(data,{Faruk:9,Mirza:9},s)[0].players,['Mirza']);
  assert.equal(D.storageKey('Faruk',{...quest,id:'dm_alba_other'}),D.storageKey('Faruk',quest));
  s.setItem(D.storageKey('Mirza',quest),'1');
  assert.equal(D.preparation(data,{Faruk:9,Mirza:9},s).length,0);
});

test('class-only quests do not produce reminders for the other player',()=>{
  const hunter={...quest,classes:['Hunter']};
  assert.equal(D.allowed(hunter,'Faruk'),false);assert.equal(D.allowed(hunter,'Mirza'),true);
  const own={dungeons:[{recommended_level:19,quests:[hunter]}]};
  assert.deepEqual(D.preparation(own,{Faruk:9,Mirza:9},storage())[0].players,['Mirza']);
});
