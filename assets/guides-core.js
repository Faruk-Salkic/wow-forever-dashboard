(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  else root.WowGuides=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  const HOUR=3600000;
  function state(item,now=Date.now()){
    const checked=Date.parse(item.last_success_at||'');
    if(item.status!=='ok') return item.last_success_at?'failed':'unverified';
    if(!Number.isFinite(checked)) return 'unverified';
    if(checked>now||now-checked>26*HOUR) return 'stale';
    return 'ok';
  }
  function changedRecently(item,now=Date.now()){
    const changed=Date.parse(item.changed_at||'');
    return Number.isFinite(changed)&&changed<=now&&now-changed<7*24*HOUR;
  }
  function forPlayer(data,player){
    return (data.items||[]).filter(item=>item.player===player).slice(0,2);
  }
  return {state,changedRecently,forPlayer};
});
