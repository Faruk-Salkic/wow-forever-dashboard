/* Shared, DOM-free allocation rules. UI drafts never change the game client. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.WowPlanner = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const total = ranks => Object.values(ranks).reduce((s, v) => s + v, 0);
  const nodes = def => def.trees.flatMap(t => t.nodes);
  const classBudget = (level, talented = 0) => Math.max(0, Math.min(51, Math.trunc(level) - 9 + Math.max(0, Math.min(5, talented))));

  function validate(def, ranks, budget) {
    const all = nodes(def), byId = Object.fromEntries(all.map(n => [n.id, n]));
    if (!Number.isInteger(budget) || budget < 0 || budget > (def.kind === 'legacy' ? 16 : 51)) return 'Ungültiges Punktebudget.';
    for (const [id, rank] of Object.entries(ranks)) {
      if (!byId[id] || !Number.isInteger(rank) || rank < 0 || rank > byId[id].max) return 'Ungültiger Talentrang.';
    }
    if (total(ranks) > budget) return 'Alle verfügbaren Punkte sind verplant.';
    for (const tree of def.trees) {
      for (const node of tree.nodes) {
        if (!(ranks[node.id] > 0)) continue;
        const spent = tree.nodes.reduce((sum, other) => sum + ((def.kind === 'class' ? other.row < node.row : other.gate < node.gate) ? ranks[other.id] || 0 : 0), 0);
        if (spent < node.gate) return `${node.name}: zuerst ${node.gate} Punkte ${def.kind === 'class' ? 'in niedrigeren Reihen' : 'im selben Baum'} setzen.`;
        const parent = byId[node.requires];
        if (parent && (ranks[parent.id] || 0) < parent.max) return `${node.name} benötigt ${parent.name} ${parent.max}/${parent.max}.`;
      }
    }
    return '';
  }

  function change(def, ranks, id, delta, budget) {
    if (delta !== 1 && delta !== -1) return {ok: false, error: 'Nur einen Punkt pro Schritt setzen.'};
    const next = {...ranks, [id]: (ranks[id] || 0) + delta};
    const error = validate(def, next, budget);
    if (error) return {ok: false, error};
    if (!next[id]) delete next[id];
    return {ok: true, ranks: next};
  }

  // Replays a saved learning order, so a budget reduction cannot leave dangling prerequisites.
  function replay(def, order, budget) {
    let ranks = {}, accepted = [], pending = [...(order || [])];
    // A manual removal can move a required lower-row point later in the saved order.
    // Retry remaining points after prerequisites are restored rather than silently losing them.
    while (pending.length && total(ranks) < budget) {
      const left = [];
      for (const id of pending) {
        const result = change(def, ranks, id, 1, budget);
        if (result.ok) { ranks = result.ranks; accepted.push(id); }
        else left.push(id);
      }
      if (left.length === pending.length) break;
      pending = left;
    }
    return {ranks, order: accepted};
  }

  function makePlan(def, chunks) {
    const all = nodes(def), order = [];
    for (const [name, count] of chunks) {
      const node = all.find(n => n.name === name);
      if (!node) throw new Error(`Talent fehlt im Datenstand: ${name}`);
      for (let i = 0; i < count; i++) order.push(node.id);
    }
    const result = replay(def, order, def.kind === 'legacy' ? 16 : 51);
    if (result.order.length !== order.length) throw new Error('Der Vorschlag passt nicht zu diesem Talent-Datenstand.');
    return order;
  }

  function classPlan(def, player) {
    return makePlan(def, player === 'Faruk' ? [
      ['Thundering Strikes',5],['Mental Dexterity',3],['Improved Ghost Wolf',2],
      ['Shamanistic Focus',1],['Elemental Weapons',3],['Ancestral Knowledge',1],
      ['Stormstrike',1],['Flurry',4],['Spirit Weapons',1],['Mental Quickness',2],
      ['Improved Stormstrike',2],['Maelstrom Weapon',5],['Rage of the Farseer',1],
      ['Flurry',1],['Ancestral Knowledge',4],['Improved Healing Wave',5],
      ['Totemic Focus',5],['Water Shield',1],['Mindfulness',3],['Natural Grace',1]
    ] : [
      ['Deadly Aspects',5],['Focused Fire',2],['Improved Revive Pet',2],['Endurance Training',1],
      ['Pathfinding',2],['Unleashed Fury',3],['Summon Hawk',1],['Unleashed Fury',2],
      ['Bestial Swiftness',1],['Ferocity',1],['Intimidation',1],['Ferocity',4],
      ['Frenzy',5],['Bestial Wrath',1],['Bestial Discipline',2],['Spirit Bond',2],
      ['Endurance Training',1],['Lethal Attacks',5],['Careful Aim',5],['Efficiency',5]
    ]);
  }

  function legacyPlan(def, focus, professions) {
    const gathering = professions.filter(p => ['Bergbau','Kräuterkunde','Kürschnerei'].includes(p)).length;
    const trade = focus === 'crafting' ? 'Working Overtime' : (gathering >= 1 ? 'Bountiful Harvest' : 'Working Overtime');
    if (focus === 'professions' || focus === 'crafting') return makePlan(def, [
      [trade,5],['Bartering',2],[trade === 'Bountiful Harvest' ? 'Working Overtime' : 'Bountiful Harvest',3],
      ['Dedicated Study',1],['Thrill of Adventure',5]
    ]);
    if (focus === 'leveling') return makePlan(def, [
      ['Thrill of Adventure',5],['Well Rested',5],['Talented',5],['Field Medicine',1]
    ]);
    return makePlan(def, [
      [trade,5],['Thrill of Adventure',5],['Bartering',2],['Field Guide',3],['Field Medicine',1]
    ]);
  }

  function restore(def, saved, budget) {
    if (!saved || !Array.isArray(saved.order)) return {ranks:{}, order:[]};
    return replay(def, saved.order.filter(id => typeof id === 'string'), budget);
  }
  return {total, nodes, classBudget, validate, change, replay, makePlan, classPlan, legacyPlan, restore};
});
