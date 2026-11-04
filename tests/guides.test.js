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

test('launch cadence detects a missed two-hour refresh sooner than daily mode',()=>{
  const guide={status:'ok',last_success_at:'2026-11-03T06:00:00Z'};
  assert.equal(Guides.state(guide,now,4),'stale');
  assert.equal(Guides.state(guide,now,26),'ok');
});

test('a cached launch feed uses daily freshness after the cutoff, before the next daily run',()=>{
  const policy={mode:'launch',interval_hours:2,frequent_until:'2026-11-19T00:00:00+01:00'};
  assert.equal(Guides.refreshPolicy(policy,Date.parse('2026-11-18T22:59:00Z')).interval_hours,2);
  assert.equal(Guides.refreshPolicy(policy,Date.parse('2026-11-18T23:00:00Z')).interval_hours,24);
  assert.equal(policy.interval_hours,2);
});

test('persistent guide links remain available even when news are older than seven days',()=>{
  const faruk={player:'Faruk',source_updated_at:'2026-10-01'};
  const mirza={player:'Mirza',source_updated_at:'2026-10-01'};
  assert.deepEqual(Guides.forPlayer({items:[faruk,mirza]},'Faruk'),[faruk]);
  assert.deepEqual(Guides.forPlayer({items:[faruk,mirza]},'Mirza'),[mirza]);
});

test('mixed Gemini results keep successful summaries available in the status message',()=>{
  const mixed=Guides.aiNotice({status:'error',succeeded:8,failed:2});
  const unavailable=Guides.aiNotice({status:'error',succeeded:0,failed:1});
  assert.match(mixed,/Einzelne neue Kurzberichte/);
  assert.match(mixed,/Bereits erstellte Zusammenfassungen bleiben sichtbar/);
  assert.notEqual(mixed,unavailable);
  assert.match(unavailable,/Neue automatische Kurzberichte/);
  assert.equal(Guides.aiNotice({status:'ok',succeeded:10,failed:0}),'');
  assert.equal(Guides.aiNotice(),'');
});
