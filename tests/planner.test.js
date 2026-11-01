const {test}=require('node:test');
const assert=require('node:assert/strict');
const C=require('../assets/planner-core.js');
const D=require('../data/planner.json');

for (const player of ['Faruk','Mirza']) {
  const def=D.classes[player==='Faruk'?'Shaman':'Hunter'];
  test(`${player}: every leveling point is legal, including all 51 points`,()=>{
    const order=C.classPlan(def,player);
    assert.equal(order.length,51);
    for(let rank=0;rank<=5;rank++) for(let level=1;level<=60;level++) {
      const cap=C.classBudget(level,rank),build=C.replay(def,order,cap);
      assert.equal(build.order.length,cap);
      assert.equal(C.validate(def,build.ranks,cap),'');
    }
  });
  test(`${player}: level budget, rank cap, prerequisites and restoration`,()=>{
    const order=C.classPlan(def,player), first=C.nodes(def).find(n=>n.id===order[0]);
    assert.equal(C.change(def,{},first.id,1,0).ok,false);
    let build=C.replay(def,order,20);
    assert.equal(C.change(def,build.ranks,first.id,1,51).ok,false);
    const dependent=C.nodes(def).find(n=>n.requires && (build.ranks[n.id]||0)>0);
    if(dependent) assert.equal(C.change(def,build.ranks,dependent.requires,-1,51).ok,false);
    const roundtrip=JSON.parse(JSON.stringify({order:build.order}));
    assert.deepEqual(C.restore(def,roundtrip,20),build);
    const reduced=C.restore(def,roundtrip,6);
    assert.equal(C.total(reduced.ranks),6);
    assert.equal(C.validate(def,reduced.ranks,6),'');
    assert.equal(C.change(def,{},'unknown-node',1,51).ok,false);
    assert.equal(C.change(def,{},first.id,-1,51).ok,false);
  });
}

test('Hunter: Pathfinding cannot be taken at level 15 without Talented',()=>{
  const def=D.classes.Hunter,order=C.classPlan(def,'Mirza');
  const node=C.nodes(def).find(n=>n.name==='Pathfinding');
  const build=C.replay(def,order,6);
  assert.equal(C.change(def,build.ranks,node.id,1,20).ok,false);
});

test('Legacy: Talented needs Well Rested 5/5, then has a shared 16-point cap',()=>{
  const def=D.legacy, byName=name=>C.nodes(def).find(n=>n.name===name).id;
  let build=C.replay(def,Array(5).fill(byName('Thrill of Adventure')),16);
  assert.equal(C.change(def,build.ranks,byName('Talented'),1,16).ok,false);
  build=C.replay(def,[...Array(5).fill(byName('Well Rested')),byName('Talented')],16);
  assert.equal(build.order.length,6);
  assert.equal(C.change(def,build.ranks,byName('Well Rested'),-1,16).ok,false);
  for(const focus of ['balanced','professions','crafting','leveling']) {
    const order=C.legacyPlan(def,focus,['Bergbau','Ingenieurskunst']);
    for(let points=0;points<=16;points++) {
      const partial=C.replay(def,order,points);
      assert.equal(partial.order.length,points);
      assert.equal(C.validate(def,partial.ranks,points),'');
    }
    const full=C.replay(def,order,16);
    const extra=C.nodes(def).find(n=>!full.ranks[n.id] && n.gate===0);
    assert.equal(C.change(def,full.ranks,extra.id,1,16).ok,false);
  }
});

test('Dataset contains the full class grids, rank texts and valid links',()=>{
  assert.deepEqual(Object.keys(D.classes).sort(),['Hunter','Shaman']);
  for(const def of [...Object.values(D.classes),D.legacy]) {
    assert.equal(def.trees.length,3);
    const ids=new Set();
    for(const tree of def.trees) {
      const cells=new Set();
      for(const n of tree.nodes) {
        assert.equal(ids.has(n.id),false);ids.add(n.id);
        assert.equal(cells.has(`${n.row}:${n.col}`),false);cells.add(`${n.row}:${n.col}`);
        assert.equal(n.ranks.length,n.max);
        assert.ok(n.row>=1 && n.col>=1 && n.col<=4 && n.ranks.every(Boolean));
        if(n.requires) assert.ok(tree.nodes.some(p=>p.id===n.requires));
      }
    }
  }
});
