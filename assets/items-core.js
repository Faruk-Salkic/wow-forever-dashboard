(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.WowItems=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function link(item,preview={}){
    const id=Number(item.id);
    if(!Number.isSafeInteger(id)||id<=0)return esc(item.name);
    const icon=/^[a-z0-9_]+$/i.test(preview.icon||'')?preview.icon:null;
    const stats=preview.stats_text||'';
    const name=item.name||preview.name||'Item '+id;
    const attrs=icon?'data-wh-iconize-link="false"':'data-wh-icon-size="small"';
    return `<a class="item-link" href="https://www.wowhead.com/forever/item=${id}" data-wowhead="item=${id}&amp;domain=de.forever" ${attrs} data-disable-wowhead-touch-tooltip="true" target="_blank" rel="noopener"${stats?` title="${esc(stats)}" aria-label="${esc(name+'. '+stats)}"`:''}>${icon?`<img class="item-icon" src="https://wow.zamimg.com/images/wow/icons/small/${icon.toLowerCase()}.jpg" width="28" height="28" alt="" loading="lazy" decoding="async">`:''}<span>${esc(name)}</span></a>`;
  }
  function refreshTooltips(){
    if(typeof window==='undefined')return;
    try{window.$WowheadPower?.refreshLinks(true);}catch(e){/* Item links stay usable if the external widget is unavailable. */}
  }
  return {link,refreshTooltips};
});
