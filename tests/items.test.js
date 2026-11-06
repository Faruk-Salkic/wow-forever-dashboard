const test=require('node:test');
const assert=require('node:assert/strict');
const I=require('../assets/items-core.js');

test('item previews use the German Forever version, keep original names and have usable fallback details',()=>{
  const html=I.link({id:271766,name:'Heavehammer'},{icon:'inv_hammer_09',stats_text:'27,73 DPS · 32 Angriffskraft'});
  assert.match(html,/href="https:\/\/www\.wowhead\.com\/forever\/item=271766"/);
  assert.match(html,/domain=de\.forever/);
  assert.match(html,/icons\/small\/inv_hammer_09\.jpg/);
  assert.match(html,/title="27,73 DPS · 32 Angriffskraft"/);
  assert.match(html,/>Heavehammer<\/span>/);
  assert.doesNotMatch(html,/domain=(?:www|classic|de\.classic)/);
  assert.doesNotThrow(()=>I.refreshTooltips());
});

test('untrusted item values cannot create executable HTML or custom image/link targets',()=>{
  const html=I.link({id:2933,name:'<img src=x onerror=alert(1)>'},{icon:'../unsafe',stats_text:'" onmouseover="bad'});
  assert.doesNotMatch(html,/<img/);
  assert.match(html,/&lt;img/);
  assert.match(html,/title="&quot; onmouseover=&quot;bad"/);
  assert.doesNotMatch(I.link({id:'javascript:alert(1)',name:'<bad>'}),/<a/);
});
