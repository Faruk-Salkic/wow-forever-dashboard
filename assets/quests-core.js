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
  return {select,recent};
});
