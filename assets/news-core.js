(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.WowNews = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const generic = /weekly recap|return to azeroth|kehre in world|1[.,]?000 (?:neue|new)|shop decor|podcast|cinematic|layering|sharding|community.building|tier.list/i;
  const permanent = /class-overview|ranged-dps-pve-guide|leveling-guide-and-talents|class-guides\/?$/i;
  function timestamp(item) {
    return Date.parse(item.is_updated && item.updated_at ? item.updated_at : item.date) || 0;
  }
  function eligible(item) {
    const text = `${item.raw_title || ''} ${item.title || ''}`;
    if (generic.test(text)) return false;
    if (item.summary_mode === 'source_unavailable') return false;
    if (item.category === 'guide' && item.date_basis === 'first_seen' && !item.specific_change) return false;
    // Permanent class guides live inside the profile, even after a generic content hash update.
    if (permanent.test((item.url || '').split('?')[0]) && !item.specific_change) return false;
    return /hotfix|exploit|bis/.test(item.category || '') || /quest|bag|tasch|vendor|händler|rezept|recipe|enchant|verzauber|pet|begleiter|tame|zähm|dungeon|loot|drop|weapon|waffe|tuning|spell|trap|cooldown|talent|fähigkeit|totem|legacy|beruf|herb|skinn|mining|party|gruppe|camp|addon/i.test(text) || (audience(item).length>0 && /change|änder|shock|nerf|buff/i.test(text));
  }
  function canonical(url) {
    try {
      const u = new URL(url); u.hash = ''; u.hostname = u.hostname.replace(/^www\./,'');
      for (const key of [...u.searchParams.keys()]) if (/^utm_|^(ref|source|src|fbclid)$/.test(key)) u.searchParams.delete(key);
      u.searchParams.sort(); return u.toString().replace(/\/$/,'');
    } catch { return url || ''; }
  }
  function tokens(item) {
    const text = (item.raw_title || item.title || '').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'');
    const stop = new Set(['world','warcraft','wow','forever','wowhead','method','icy','veins','the','in','of','for','and','a','an','fur','und','die','der','das','new','neue']);
    return new Set((text.match(/[a-z0-9]+/g) || []).filter(w => w.length > 1 && !stop.has(w)));
  }
  function sameStory(a,b) {
    if (canonical(a.url) === canonical(b.url)) return true;
    if (a.story_key && b.story_key) return a.story_key === b.story_key;
    const x=tokens(a), y=tokens(b);
    if (Math.min(x.size,y.size) < 4) return false;
    const intersection = [...x].filter(w=>y.has(w)).length;
    return intersection / (x.size + y.size - intersection) >= .84;
  }
  function audience(item) {
    const title=`${item.raw_title || ''} ${item.title || ''} ${(item.url || '').split('?')[0]}`.toLowerCase();
    const explicit=[];
    if (/\b(?:hunter|jäger|jaeger|beast.mastery|marksmanship)\b/.test(title)) explicit.push('Hunter');
    if (/\b(?:shaman|schamane|schamanen|windfury|totem)\b/.test(title)) explicit.push('Shaman');
    if (explicit.length) return explicit;
    // Practical shared guides must not inherit a class from an incidental body mention.
    if (/bag|tasch|vendor|händler|enchant|verzauber|recipe|rezept|addon|profession|beruf|dungeon|party|gruppe|camp/.test(title)) return [];
    return (item.classes || []).filter(c=>c==='Hunter'||c==='Shaman');
  }
  function selectRecent(items, now = Date.now(), scope = 'all', limit = 4) {
    const candidates = items.filter(i=>eligible(i) && timestamp(i)<=now && now-timestamp(i)<=7*864e5)
      .filter(i=>scope==='all' || (scope==='general' ? audience(i).length===0 : audience(i).includes(scope)))
      .sort((a,b)=>timestamp(b)-timestamp(a) || Number(b.category==='hotfix')-Number(a.category==='hotfix') || String(a.id).localeCompare(String(b.id)));
    const result=[];
    for (const item of candidates) if (!result.some(older=>sameStory(item,older))) result.push(item);
    return result.slice(0, limit);
  }
  const selectHome=(items,now=Date.now())=>selectRecent(items,now,'general',4);
  const selectClass=(items,cls,now=Date.now())=>selectRecent(items,now,cls,12);
  return {timestamp,eligible,canonical,sameStory,audience,selectRecent,selectHome,selectClass};
});
