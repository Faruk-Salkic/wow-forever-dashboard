/* Data-driven, browser-local build drafts for the two players. */
(function () {
  'use strict';
  const C = window.WowPlanner, mounts = new Map();
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clamp = (n,min,max) => Math.max(min, Math.min(max, parseInt(n,10) || min));
  const className = player => player === 'Faruk' ? 'Shaman' : 'Hunter';
  const key = (p,k) => `wow_planner_v1_${p}_${k}`;
  function talented(player) {
    const m=mounts.get(`${player}-legacy`);
    if (!m) return 0;
    const n=C.nodes(m.def).find(n=>n.name==='Talented');
    return m.state.ranks[n.id] || 0;
  }
  function budget(m) {
    return m.kind==='legacy' ? m.points : C.classBudget(m.state.level, talented(m.player));
  }
  function persist(m) {
    try { localStorage.setItem(key(m.player,m.kind),JSON.stringify({schema:1,version:m.data.version,level:m.state.level,focus:m.focus,order:m.state.order})); }
    catch { m.notice='Speichern ist in diesem Browser nicht verfügbar. Bitte den Build-Text sichern.'; }
  }
  function plan(m) {
    return m.kind==='legacy' ? C.legacyPlan(m.def,m.focus,m.professions()) : C.classPlan(m.def,m.player);
  }
  function reason(name,player) {
    const reasons={
      'Thundering Strikes':'Kritische Treffer für Nahkampf und Zauber; bleibt im Duo nützlich.',
      'Mental Dexterity':'Intelligenz verbessert den Nahkampf. Unterstützt Ausrüstung mit Mana und Angriffskraft.',
      'Improved Ghost Wolf':'Weniger Zeit beim Verwandeln, nützlich auf langen Laufwegen.',
      'Shamanistic Focus':'Weniger Mana für den nächsten passenden Zauber nach einem Nahkampf-Crit.',
      'Stormstrike':'Aktiver Nahkampfangriff; zentraler Schritt des Enhancement-Plans.',
      'Spirit Weapons':'Zusätzliche Defensive und Kontrolle der Bedrohung; Rockbiter-Hinweis im Originaltext beachten.',
      'Maelstrom Weapon':'Verbindet Nahkampf mit schnelleren Zaubern und Notheilung.',
      'Rage of the Farseer':'Abschluss des Enhancement-Kerns, bevor der Duo-Komfort ausgebaut wird.',
      'Water Shield':'Mana-Komfort für längere Kämpfe und unterstützende Heilung.',
      'Deadly Aspects':'Mehr Angriffstempo, wenn der passende Aspekt aktiv ist.',
      'Focused Fire':'Mehr Nutzen aus dem aktiven Begleiter.',
      'Improved Revive Pet':'Günstiger und schneller zurück ins Spiel, wenn das Pet stirbt.',
      'Pathfinding':'Schnellere Wege mit den Reise-Aspekten. Erst nach zehn Punkten in Beast Mastery erreichbar.',
      'Unleashed Fury':'Mehr Begleiterschaden, während das Pet Gegner beschäftigt.',
      'Summon Hawk':'Zusätzlicher aktiver Schaden im Beast-Mastery-Plan.',
      'Bestial Swiftness':'Das Pet kommt im Freien schneller ans Ziel; Voraussetzung für Intimidation.',
      'Intimidation':'Kontrolliert einen Gegner und hilft dem Pet, Bedrohung aufzubauen.',
      'Bestial Wrath':'Abschluss des Beast-Mastery-Kerns für starke Begleiterphasen.',
      'Thrill of Adventure':'Regeneration nach dem eigenen Todesstoß an einem relevanten Gegner. Im Duo bekommt nicht automatisch jeder den Effekt; wirkt nicht in Dungeons oder BGs.',
      'Bountiful Harvest':'Mehr Chancen auf seltene Zusatzmaterialien beim Sammeln. Verdoppelt nicht pauschal alle Erze, Kräuter oder Leder.',
      'Working Overtime':'Mehr Chancen auf einen Skillpunkt beim Ausüben eines Berufs. Bringt bei bereits sicheren Skill-ups und auf maximalem Skill weniger.',
      'Well Rested':'Erhöht Aufbau und Obergrenze von Erholt-XP. Kein pauschaler XP-Bonus; bei vielen Offline-Pausen interessanter.',
      'Talented':'Frühere Klassenpunkte, weiterhin höchstens 51. Benötigt Well Rested 5/5 und insgesamt zehn Legacy-Punkte für Rang 5; auf 60 ohne zusätzlichen Nutzen.',
      'Bartering':'Günstigere Händlerkäufe; dafür entfallen Punkte in anderen Bäumen.',
      'Dedicated Study':'Täglicher langfristiger Berufsfortschritt. Benötigt zehn andere Berufspunkte und Bartering 2/2.'
    };
    return reasons[name] || (player==='Faruk' ? 'Teil des Duo-Plans für Nahkampf, Mana und unterstützende Heilung.' : 'Teil des Duo-Plans für Begleiter, Fernkampf und weniger Pausen.');
  }
  function description(m) {
    if (m.kind==='class') return m.player==='Faruk'
      ? 'Duo-Vorschlag: Enhancement zuerst, danach Heil- und Mana-Komfort (0/36/15). Ein durchgehender Level-60-Plan, kein separater Raid- oder Heiler-Build.'
      : 'Duo-Vorschlag: Beast Mastery zuerst, danach Fernkampf-Talente (36/15/0). Für Quests und kleine Gruppen; Raid- und BG-Builds separat bewerten.';
    const ps=m.professions();
    if (m.focus==='leveling') return 'Leveln / Alt: Regeneration → Well Rested → Talented. Zehn Punkte sind allein für den Weg zu Talented 5/5 gebunden. Auf Stufe 60 bringt es keine zusätzlichen Klassenpunkte.';
    if (m.focus==='crafting') return 'Herstellen: Working Overtime zuerst, dann günstiger einkaufen und langfristig Dedicated Study freischalten. Der Vorteil hängt von den verwendeten Rezepten ab; sichere Skill-ups brauchen diesen Bonus weniger.';
    if (m.focus==='professions') return 'Berufe langfristig: Sammelbonus zuerst, dann Bartering und der Weg zu Dedicated Study. Ihr verzichtet dafür zunächst auf Regeneration. Seltene Zusatzmaterialien sind der Nutzen, kein garantierter Mehrertrag pro Knoten.';
    return `Für ${ps.join(' + ')}: zuerst Berufs-Nutzen, dann Regeneration und Komfort. Bewusster Mix statt Talented-Pflicht. Bei ständigem Mana-Mangel könnt ihr den Regenerationsweg wählen.`;
  }
  function render(m) {
    const all=C.nodes(m.def), used=C.total(m.state.ranks), cap=budget(m);
    const selected=all.find(n=>n.id===m.selected);
    const focus=document.activeElement?.closest('[data-action]');
    const focusKey=focus && m.el.contains(focus) ? [focus.dataset.action,focus.dataset.node] : null;
    let recommendations=[];
    try { recommendations=plan(m); m.planError=''; } catch(e) { m.planError=e.message; }
    const trees=m.def.trees.map(t=>{
      const maxRow=Math.max(...t.nodes.map(n=>n.row));
      const lines=t.nodes.filter(n=>n.requires).map(n=>{
        const parent=t.nodes.find(p=>p.id===n.requires);
        if (!parent) return '';
        const x=(parent.col-.5)*100,y=(parent.row-.5)*100,ex=(n.col-.5)*100,ey=(n.row-.5)*100;
        return `<path d="M ${x} ${y+18} V ${ey-26} H ${ex} V ${ey-18}" class="${(m.state.ranks[parent.id]||0)===parent.max?'met':''}"/>`;
      }).join('');
      return `<section class="planner-tree" data-current="${t.id===m.treeFocus}"><h4>${esc(t.name)} <span>${t.nodes.reduce((s,n)=>s+(m.state.ranks[n.id]||0),0)} Punkte</span></h4>
        <div class="planner-grid" style="--rows:${maxRow}"><svg class="planner-links" viewBox="0 0 400 ${maxRow*100}" preserveAspectRatio="none" aria-hidden="true">${lines}</svg>
        ${t.nodes.map(n=>{
          const rank=m.state.ranks[n.id]||0, plus=C.change(m.def,m.state.ranks,n.id,1,cap), minus=rank?C.change(m.def,m.state.ranks,n.id,-1,cap):{ok:false};
          return `<div class="planner-node ${rank===n.max?'maxed':rank?'allocated':''} ${m.selected===n.id?'selected':''}" style="grid-row:${n.row};grid-column:${n.col}">
            <button type="button" class="planner-pick" data-action="inspect" data-node="${n.id}" aria-label="${esc(n.name)}, Rang ${rank} von ${n.max}, Details" title="${esc(n.name)}"><img src="https://wow.zamimg.com/images/wow/icons/large/${esc(n.icon)}.jpg" loading="lazy" alt="" width="36" height="36"><span>${esc(n.name)}</span></button>
            <div class="rank-controls"><button type="button" data-action="remove" data-node="${n.id}" aria-label="${esc(n.name)}: Punkt entfernen" ${minus.ok?'':'disabled'}>−</button><b>${rank}/${n.max}</b><button type="button" data-action="add" data-node="${n.id}" aria-label="${esc(n.name)}: Punkt setzen" ${plus.ok?'':'disabled'}>+</button></div>
          </div>`;
        }).join('')}</div></section>`;
    }).join('');
    const rank=selected?(m.state.ranks[selected.id]||0):0;
    const detail=selected ? `<h4>${esc(selected.name)} <small>${rank}/${selected.max}</small></h4><p>${esc(reason(selected.name,m.player))}</p><p class="planner-original"><strong>Originaltext ${rank?`(Rang ${rank})`:'(nächster Rang)'}:</strong> ${esc(selected.ranks[Math.max(0,rank-1)])}</p>${rank<selected.max && rank>0?`<p class="planner-original"><strong>Nächster Rang:</strong> ${esc(selected.ranks[rank])}</p>`:''}<small>${selected.gate?`${selected.gate} Punkte ${m.kind==='class'?'in niedrigeren Reihen':'im selben Baum'}. `:''}${selected.requires?`Voraussetzung: ${esc(all.find(n=>n.id===selected.requires).name)} auf höchstem Rang. `:''}${esc(selected.cost)}</small>` : '<p>Ein Icon öffnet Wirkung und Voraussetzungen. Mit + und − plant ihr die Punkte.</p>';
    const controls=m.kind==='class' ? `<label>Planungsstufe <input aria-label="Planungsstufe ${m.player}" data-action="level" type="number" min="1" max="60" value="${m.state.level}"></label><button type="button" data-action="recommend">Vorschlag für meine Stufe (${m.level()})</button><button type="button" data-action="full">Level-60-Vorschlag</button>`
      : `<label>Bereits freigeschaltete Punkte <input aria-label="Legacy-Punkte ${m.player}" data-action="points" type="number" min="0" max="16" value="${m.points}"></label><label>Ziel <select data-action="focus"><option value="balanced" ${m.focus==='balanced'?'selected':''}>Berufe + Duo</option><option value="professions" ${m.focus==='professions'?'selected':''}>Langfristig: Sammeln</option><option value="crafting" ${m.focus==='crafting'?'selected':''}>Langfristig: Herstellen</option><option value="leveling" ${m.focus==='leveling'?'selected':''}>Leveln / Alt</option></select></label><button type="button" data-action="recommend">Vorschlag für ${m.points} Punkte laden</button>`;
    m.el.innerHTML=`<div class="planner-intro"><p>${esc(description(m))}</p><span class="planner-counter">${used} / ${cap} verplant · ${cap-used} frei</span></div>
      <div class="planner-toolbar">${controls}<button type="button" data-action="reset">Entwurf leeren</button><label class="planner-tree-mobile">Baum <select data-action="tree" aria-label="Talentbaum ${m.player} ${m.kind}">${m.def.trees.map(t=>`<option value="${t.id}" ${t.id===m.treeFocus?'selected':''}>${esc(t.name)}</option>`).join('')}</select></label></div>
      ${m.kind==='legacy'?'<p class="planner-note">16 Punkte insgesamt über alle drei Bäume. Beim ersten Charakter startet ihr mit 0; Herausforderungen schalten Punkte accountweit frei, beispielsweise erstmals Stufe 25. Ein späterer Charakter kann bereits freigeschaltete Punkte früher nutzen. Ingame-Reset beim Hauptstadt-Klassentrainer, gegen Gebühr; der endgültige Live-Preis ist nicht bestätigt.</p>':`<p class="planner-note">Plan und Level im Spiel sind getrennt. Talented im Legacy-Entwurf: ${talented(m.player)}/5 · höchstens 51 Klassenpunkte. Der Vorschlag ist eine begründete Duo-Planung, kein gemessener Live-Bestwert.</p>`}
      <p class="planner-status" role="status" aria-live="polite">${esc(m.notice||m.planError||'Entwurf wird nur in diesem Browser gespeichert.')}</p>
      <div class="planner-trees">${trees}</div><div class="planner-detail">${detail}</div>
      <details class="planner-order"><summary>${m.kind==='class'?'Punkt für Punkt bis Level 60':'Reihenfolge des gewählten Vorschlags'}</summary><ol>${recommendations.map((id,i)=>{
        const n=all.find(n=>n.id===id), nextRank=recommendations.slice(0,i+1).filter(x=>x===id).length;
        return `<li><b>${m.kind==='class'?`Stufe ${Math.max(5,10-talented(m.player))+i}`:`Punkt ${i+1}`}</b>: ${esc(n.name)} ${nextRank}/${n.max}<span>${esc(reason(n.name,m.player))}</span></li>`;
      }).join('')}</ol></details>
      <details class="planner-export"><summary>Build sichern oder importieren</summary><p>Getrennt für ${m.player}; ein Import ersetzt nur diesen Entwurf.</p><textarea aria-label="Build-Text ${m.player} ${m.kind}" rows="3" spellcheck="false">${esc(JSON.stringify({schema:1,version:m.data.version,player:m.player,class:className(m.player),kind:m.kind,level:m.state.level,points:m.points,order:m.state.order}))}</textarea><button type="button" data-action="copy">Build-Text kopieren</button> <button type="button" data-action="import">Text importieren</button></details>
      <p class="planner-source">Daten: <a href="https://talentsforever.com/about" target="_blank" rel="noopener">Talents Forever</a>, CC BY 4.0, Export ${esc(m.data.generated)}. ${esc(m.kind==='class'?m.def.source_note:m.data.notice)} Spieltexte und Icons: Blizzard Entertainment. ${m.kind==='class'?'<a href="https://www.wowhead.com/forever/talent-calc/'+className(m.player).toLowerCase()+'" target="_blank" rel="noopener">Wowhead-Vergleich ↗</a>':'<a href="https://www.method.gg/wow-forever/legacy-calculator" target="_blank" rel="noopener">Method-Vergleich ↗</a>'}</p>`;
    if (focusKey) [...m.el.querySelectorAll('[data-action]')].find(e=>e.dataset.action===focusKey[0] && e.dataset.node===focusKey[1])?.focus({preventScroll:true});
  }
  function notifyClass(player) {
    const m=mounts.get(`${player}-class`); if (!m) return;
    // Keep a manual draft intact when a Legacy change reduces its available points.
    while (C.total(m.state.ranks)>budget(m) && m.state.level<60) m.state.level++;
    render(m); persist(m); m.changed?.();
  }
  async function handle(m,event) {
    const button=event.target.closest('[data-action]'); if (!button || !m.el.contains(button)) return;
    const action=button.dataset.action;
    if (event.type==='click' && ['level','points','focus','tree'].includes(action)) return;
    if (event.type==='change' && !['level','points','focus','tree'].includes(action)) return;
    if (event.type==='input' && (!['level','points'].includes(action) || button.value==='')) return;
    m.notice='';
    if (action==='inspect') m.selected=button.dataset.node;
    if (action==='add' || action==='remove') {
      const id=button.dataset.node, delta=action==='add'?1:-1, result=C.change(m.def,m.state.ranks,id,delta,budget(m));
      if (!result.ok) m.notice=result.error;
      else {
        m.state.ranks=result.ranks;
        if (delta>0) m.state.order.push(id); else m.state.order.splice(m.state.order.lastIndexOf(id),1);
        m.selected=id;
      }
    }
    if (action==='level') {
      const next=clamp(button.value,1,60);
      if (C.total(m.state.ranks)>C.classBudget(next,talented(m.player))) m.notice='Für diese Stufe sind zu viele Punkte verplant. Erst Punkte entfernen oder den passenden Vorschlag laden.';
      else m.state.level=next;
    }
    if (action==='points') {
      m.points=clamp(button.value,0,16); m.state={...m.state,...C.replay(m.def,m.state.order,m.points)};
      m.setPoints(m.points); m.notice='Punktebudget gespeichert. Der Entwurf wurde an das verfügbare Budget angepasst.';
    }
    if (action==='focus') m.focus=button.value;
    if (action==='tree') m.treeFocus=button.value;
    if (action==='reset') m.state={...m.state,ranks:{},order:[]};
    if (action==='recommend' || action==='full') {
      try {
        if (m.kind==='class') m.state.level=action==='full'?60:m.level();
        m.state={...m.state,...C.replay(m.def,plan(m),budget(m))};
        m.notice='Vorschlag in den Entwurf geladen. Eure Stufe im Spiel wurde nicht verändert.';
      } catch(e) { m.notice=e.message; }
    }
    if (action==='copy') {
      const area=m.el.querySelector('textarea');
      try { await navigator.clipboard.writeText(area.value); m.notice='Build-Text kopiert.'; }
      catch { area.select(); m.notice='Build-Text markieren und mit Strg+C kopieren.'; m.el.querySelector('[role=status]').textContent=m.notice; return; }
    }
    if (action==='import') {
      try {
        const text=m.el.querySelector('textarea').value;
        if (text.length>30000) throw new Error('Build-Text ist zu lang.');
        const value=JSON.parse(text);
        if (value.schema!==1 || value.class!==className(m.player) || value.kind!==m.kind || !Array.isArray(value.order)) throw new Error('Dieser Build gehört zu einer anderen Klasse oder einem anderen Rechner.');
        const lvl=clamp(value.level,1,60), cap=m.kind==='legacy'?m.points:C.classBudget(lvl,talented(m.player));
        const restored=C.restore(m.def,value,cap);
        if (restored.order.length!==value.order.length) throw new Error('Build passt nicht zu den verfügbaren Punkten oder zum Datenstand. Entwurf bleibt erhalten.');
        m.state={...restored,level:lvl}; m.notice='Build importiert.';
      } catch(e) { m.notice=e.message || 'Ungültiger Build-Text.'; }
    }
    persist(m); render(m);
    if (m.kind==='legacy') notifyClass(m.player);
    m.changed?.();
  }
  function mount(options) {
    const {player,kind,data,el}=options;
    const m={...options,def:kind==='class'?data.classes[className(player)]:data.legacy,focus:'balanced',treeFocus:kind==='legacy'?'professions':player==='Faruk'?'enhancement':'beast-mastery',notice:''};
    let saved=null;
    try { saved=JSON.parse(localStorage.getItem(key(player,kind))||'null'); } catch { m.notice='Gespeicherter Build konnte nicht gelesen werden. Exportierte Sicherung verwenden.'; }
    if (['balanced','professions','crafting','leveling'].includes(saved?.focus)) m.focus=saved.focus;
    const level=clamp(saved?.level||m.level(),1,60);
    m.state={...C.restore(m.def,saved,kind==='legacy'?m.points:C.classBudget(level,talented(player))),level};
    if (saved && (saved.version!==data.version || saved.order?.length!==m.state.order.length)) m.notice='Datenstand geändert: Entwurf geprüft. Nicht mehr gültige Punkte wurden entfernt.';
    mounts.set(`${player}-${kind}`,m);
    el.addEventListener('click',e=>handle(m,e)); el.addEventListener('change',e=>handle(m,e)); el.addEventListener('input',e=>handle(m,e));
    render(m); return m;
  }
  window.PlannerUI={mount,talented,reason,refresh(player){ for (const kind of ['class','legacy']) { const m=mounts.get(`${player}-${kind}`); if(m) render(m); } }};
})();
