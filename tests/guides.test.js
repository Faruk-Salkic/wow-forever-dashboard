const test=require('node:test');
const assert=require('node:assert/strict');
const Guides=require('../assets/guides-core.js');
const now=Date.parse('2026-11-03T11:00:00Z');

test('guide failures and missed daily runs cannot look freshly verified',()=>{
  const good={status:'ok',last_success_at:'2026-11-02T11:50:00Z'};
  assert.equal(Guides.state(good,now),'ok');
  assert.equal(Guides.state({...good,last_success_at:'2026-11-01T11:50:00Z'},now),'stale');
  assert.equal(Guides.state({...good,status:'error',checked_at:'2026-11-03T10:59:00Z'},now),'failed');
  assert.equal(Guides.state({status:'error'},now),'unverified');
  assert.equal(Guides.state({status:'ok'},now),'unverified');
});

test('a successful recheck alone does not produce an update badge',()=>{
  assert.equal(Guides.changedRecently({checked_at:'2026-11-03T10:59:00Z'},now),false);
  assert.equal(Guides.changedRecently({changed_at:'2026-11-03T10:59:00Z'},now),true);
  assert.equal(Guides.changedRecently({changed_at:'2026-11-04T10:59:00Z'},now),false);
  assert.equal(Guides.changedRecently({changed_at:'2026-10-20T10:59:00Z'},now),false);
});

test('persistent guide links remain available even when news are older than seven days',()=>{
  const faruk={player:'Faruk',source_updated_at:'2026-10-01'};
  const mirza={player:'Mirza',source_updated_at:'2026-10-01'};
  assert.deepEqual(Guides.forPlayer({items:[faruk,mirza]},'Faruk'),[faruk]);
  assert.deepEqual(Guides.forPlayer({items:[faruk,mirza]},'Mirza'),[mirza]);
});
