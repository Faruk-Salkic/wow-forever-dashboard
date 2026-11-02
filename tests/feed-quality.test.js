const test=require('node:test');
const assert=require('node:assert/strict');
const News=require('../assets/news-core.js');
test('more Reddit sources cannot displace useful news with placeholders or generic requests',()=>{
  const base={category:'news',date:new Date().toISOString(),url:'https://example.test/story',summary_mode:'curated'};
  const good={...base,id:'useful',raw_title:'New quest reward bag in Dun Morogh'};
  const items=[
    {...base,id:'empty',raw_title:'WoW Forever Skinning Guide',summary_mode:'untranslated'},
    {...base,id:'generic',raw_title:'Add-on'},
    {...base,id:'opinion',raw_title:'We need better incentives for a full 5man dungeon group'},
    good
  ];
  assert.deepEqual(News.selectHome(items),[good]);
});
