const {test}=require('node:test');
const assert=require('node:assert/strict');
const N=require('../assets/news-core.js');
const now=Date.parse('2026-11-01T20:00:00Z');
const item=(id,title,date,extra={})=>({id,title,raw_title:title,url:`https://example.org/${id}`,category:'guide',date,...extra});

test('Home uses current useful stories, not the first array entries or a source quota',()=>{
  const old=item('old','WoW Forever: Rare Hunter quest reward','2026-10-01');
  const overview=item('overview','Icy Veins Hunter Overview','2026-11-01',{url:'https://www.icy-veins.com/wow-forever/hunter-class-overview',is_updated:true,updated_at:'2026-11-01'});
  const recap=item('recap','WoW Forever Weekly Recap: New Shop Decor','2026-11-01');
  const q1=item('q1','WoW Forever quest reward: Canvas Latchbag','2026-10-31',{source:'Method'});
  const q2=item('q2','WoW Forever quest reward: Copper Battle Axe','2026-11-01',{source:'Method'});
  const future=item('future','Hunter pet taming location','2026-11-03');
  assert.deepEqual(N.selectHome([overview,old,recap,q1,q2,future],now).map(i=>i.id),['q2','q1']);
});
test('Different quests in the same class/category survive deduplication; updated duplicates do not',()=>{
  const a=item('a','Hunter quest: The Green Hills reward','2026-11-01');
  const b=item('b','Hunter quest: The Great Hunt reward','2026-11-01');
  const dup={...a,id:'a2',url:a.url+'?utm_source=feed',is_updated:true,updated_at:'2026-11-01'};
  assert.equal(N.selectClass([a,b,dup],'Hunter',now).length,2);
  assert.equal(N.sameStory(a,b),false);
});
test('Cross-source identical headlines are one event; separate hotfixes remain distinct',()=>{
  const a=item('a','WoW Forever Hunter Summon Hawk cooldown hotfix','2026-11-01',{category:'hotfix'});
  const b=item('b','Wowhead: WoW Forever Hunter Summon Hawk cooldown hotfix','2026-11-01',{category:'hotfix'});
  const c=item('c','WoW Forever Hunter pet armor scaling hotfix','2026-11-01',{category:'hotfix'});
  assert.equal(N.selectClass([a,b,c],'Hunter',now).length,2);
});
test('Home never exceeds four stories and uses update time for genuine changes',()=>{
  const list=Array.from({length:8},(_,n)=>item('q'+n,`Quest location ${n}: ${['Bag','Axe','Wolf','Bear','Cave','Tower','Forest','River'][n]}`,'2026-10-31'));
  list.push(item('changed','Hunter pet ability Dash changed','2026-09-01',{is_updated:true,updated_at:'2026-11-01T19:00:00Z'}));
  const chosen=N.selectRecent(list,now);assert.equal(chosen.length,4);assert.equal(chosen[0].id,'changed');
});
test('Discovering a permanent guide today is not a publication or a verified update',()=>{
  const unknown=item('unknown','Forever Engineering recipe guide','2026-11-01',{date_basis:'first_seen'});
  const unavailable=item('failed','Hunter spell tuning','2026-11-01',{summary_mode:'source_unavailable'});
  assert.deepEqual(N.selectHome([unknown,unavailable],now),[]);
});

test('General news and class updates are routed to their own pages',()=>{
  const hunter=item('hunter','WoW Forever Hunter trap cooldown hotfix','2026-11-01',{classes:['Hunter','Shaman']});
  const shaman=item('shaman','WoW Forever Shaman Earth Shock change','2026-11-01',{classes:['Shaman']});
  const bags=item('bags','Early bag vendor quest rewards in WoW Forever','2026-11-01',{classes:['Hunter']});
  const both=item('both','WoW Forever Hunter and Shaman spell hotfix','2026-11-01',{classes:['Hunter','Shaman']});
  const all=[hunter,shaman,bags,both];
  assert.deepEqual(N.selectHome(all,now).map(x=>x.id),['bags']);
  assert.deepEqual(new Set(N.selectClass(all,'Hunter',now).map(x=>x.id)),new Set(['hunter','both']));
  assert.deepEqual(new Set(N.selectClass(all,'Shaman',now).map(x=>x.id)),new Set(['shaman','both']));
});
