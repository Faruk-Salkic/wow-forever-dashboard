(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.WowQuests=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  const recent=(item,now=Date.now())=>!!item.changed_at&&Date.parse(item.changed_at)<=now&&now-Date.parse(item.changed_at)<7*864e5;
  function select(items,levels,player=null){
    const cls=player==='Faruk'?'Shaman':'Hunter';
    const list=items.filter(q=>player?q.classes.includes(cls):q.classes.length===0);
    const active=player?[levels[player]]:Object.values(levels);
    const distance=q=>Math.min(...active.map(level=>Math.abs(q.level-level)));
    return list.filter(q=>active.some(level=>q.level>=level-8&&q.min_level<=level+10))
      .sort((a,b)=>Number(recent(b))-Number(recent(a))||distance(a)-distance(b)||a.id-b.id).slice(0,player?2:3);
  }
  function classHints(items,levels,player){
    const level=levels[player]||1;
    return items.filter(x=>x.players?.length===1&&x.players[0]===player)
      .filter(x=>x.quest_gear?level<=x.max_level:level+7>=x.min_level&&level<=x.max_level)
      .sort((a,b)=>Number(!!b.quest_gear)-Number(!!a.quest_gear)||
        (a.quest_gear&&b.quest_gear?Math.abs(a.min_level-level)-Math.abs(b.min_level-level):0)||
        (b.priority||0)-(a.priority||0));
  }
  return {select,recent,classHints};
});
