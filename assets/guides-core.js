(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  else root.WowGuides=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  const HOUR=3600000;
  function state(item,now=Date.now(),maxAgeHours=26){
    const checked=Date.parse(item.last_success_at||'');
    if(item.status!=='ok') return item.last_success_at?'failed':'unverified';
    if(!Number.isFinite(checked)) return 'unverified';
    if(checked>now||now-checked>maxAgeHours*HOUR) return 'stale';
    return 'ok';
  }
  function changedRecently(item,now=Date.now()){
    const changed=Date.parse(item.changed_at||'');
    return Number.isFinite(changed)&&changed<=now&&now-changed<7*24*HOUR;
  }
  function forPlayer(data,player){
    return (data.items||[]).filter(item=>item.player===player).slice(0,2);
  }
  function refreshPolicy(policy,now=Date.now()){
    const value=policy||{interval_hours:24};
    if(value.mode==='launch'&&now>=Date.parse(value.frequent_until))
      return {...value,mode:'daily',interval_hours:24,description_de:'Tägliche Quellenprüfung um 11:50 (Wien).'};
    return value;
  }
  function aiNotice(status={}){
    if(Number(status.succeeded)>0&&Number(status.failed)>0)
      return 'Einzelne neue Kurzberichte sind derzeit nicht verfügbar. Bereits erstellte Zusammenfassungen bleiben sichtbar.';
    if(status.status==='error')
      return 'Neue automatische Kurzberichte sind derzeit nicht verfügbar. Quellen und Quest-Hinweise werden weiter geprüft.';
    return '';
  }
  return {state,changedRecently,forPlayer,refreshPolicy,aiNotice};
});
