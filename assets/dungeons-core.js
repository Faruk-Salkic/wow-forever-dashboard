(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.WowDungeons=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  const players=['Faruk','Mirza'];
  const allowed=(q,p)=>!q.classes?.length||q.classes.includes(p==='Faruk'?'Shaman':'Hunter');
  const storageKey=(p,q)=>'wow_quest_'+p+'_'+(q.progress_id||q.id);
  const done=(q,p,storage)=>storage.getItem(storageKey(p,q))==='1';
  function preparation(data,levels,storage){
    const rows=[];
    for(const d of data.dungeons||[])for(const q of d.quests||[]){
      if(q.phase!=='before'||!q.location_confirmed)continue;
      const start=q.prepare_from_level||q.min_lvl;
      const needed=players.filter(p=>allowed(q,p)&&!done(q,p,storage)&&levels[p]<=q.min_lvl+12&&start<=levels[p]+10);
      if(!needed.length)continue;
      const gap=Math.min(...needed.map(p=>Math.abs(start-levels[p])));
      rows.push({dungeon:d,quest:q,players:needed,ready:needed.some(p=>levels[p]>=start),gap});
    }
    return rows.sort((a,b)=>a.gap-b.gap||Number(b.quest.requires_chain)-Number(a.quest.requires_chain)||Number(b.ready)-Number(a.ready)||a.quest.game_id-b.quest.game_id).slice(0,6);
  }
  function visible(data,levels,all=false){
    return (data.dungeons||[]).map(d=>({...d,quests:(d.quests||[]).filter(q=>all||players.some(p=>allowed(q,p)&&q.min_lvl<=levels[p]+10&&(d.recommended_level||q.min_lvl)>=levels[p]-8))}))
      .filter(d=>all||d.quests.length);
  }
  return {allowed,storageKey,done,preparation,visible};
});
