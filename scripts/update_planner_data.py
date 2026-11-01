"""Refresh the attributed, licensed data snapshot; keep the last good data on upstream errors."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
SOURCE='https://talentsforever.com/data.json'

def slug(value): return re.sub(r'[^a-z0-9]+','-',value.lower()).strip('-')

def convert_tree(tree,kind):
    nodes=[]
    for raw in tree.get('talents',tree.get('perks',[])):
        if raw.get('placeholder'): continue
        ranks=raw.get('desc',raw.get('ranks',[]))
        if not ranks or len(ranks)!=raw['max'] or not all(isinstance(r,str) and r for r in ranks): raise ValueError('Incomplete rank texts')
        nodes.append(dict(id=slug(tree['name'])+'-'+slug(raw['name']),name=raw['name'],max=raw['max'],row=raw['row'],col=raw['col'],icon=raw['icon'],ranks=ranks,gate=raw.get('gate',(raw['row']-1)*5 if kind=='class' else 0),requires=raw.get('req'),cost=raw.get('cost','')))
    by_name={n['name']:n['id'] for n in nodes}
    for node in nodes:
        if node['requires']: node['requires']=by_name[node['requires']]
    return dict(id=slug(tree['name']),name=tree['name'],nodes=nodes)

def convert(raw,old):
    if raw.get('license')!='CC-BY-4.0': raise ValueError('Upstream licence changed; review required')
    classes={name:dict(kind='class',source_note=raw['talents'][name]['source'],trees=[convert_tree(t,'class') for t in raw['talents'][name]['trees']]) for name in ['Shaman','Hunter']}
    legacy=dict(kind='legacy',trees=[convert_tree(t,'legacy') for t in raw['legacy']['trees']])
    for entry in [*classes.values(),legacy]:
        if len(entry['trees'])!=3: raise ValueError('Missing tree')
    for name,entry in classes.items():
        if sum(len(t['nodes']) for t in entry['trees'])<40: raise ValueError('Partial class data')
    if sum(len(t['nodes']) for t in legacy['trees'])<20: raise ValueError('Partial Legacy data')
    content={'classes':classes,'legacy':legacy}
    fingerprint=hashlib.sha256(json.dumps(content,sort_keys=True).encode()).hexdigest()[:10]
    same=all(old.get(k)==v for k,v in content.items())
    return {**old,**content,'schema':1,'version':old['version'] if same else fingerprint,'generated':raw['generated'],'source':SOURCE,'source_page':'https://talentsforever.com/about','license':raw['license'],'attribution':raw['attribution']}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--from-file',type=Path)
    parser.add_argument('--keep-on-error',action='store_true')
    args=parser.parse_args()
    try:
        if args.from_file: raw=json.loads(args.from_file.read_text(encoding='utf8'))
        else:
            with urllib.request.urlopen(SOURCE,timeout=20) as response: raw=json.load(response)
        path=ROOT/'data/planner.json';old=json.loads(path.read_text(encoding='utf8'));new=convert(raw,old)
        # Validate the complete recommended sequences against the incoming grid, before replacing data.
        with tempfile.TemporaryDirectory() as tmp:
            candidate=Path(tmp)/'candidate.json';candidate.write_text(json.dumps(new),encoding='utf8')
            check="const C=require(process.argv[1]),D=require(process.argv[2]);for(const p of ['Faruk','Mirza']){const d=D.classes[p==='Faruk'?'Shaman':'Hunter'];if(C.classPlan(d,p).length!==51)throw Error('Invalid class plan');}for(const f of ['balanced','professions','crafting','leveling'])if(C.legacyPlan(D.legacy,f,['Bergbau','Ingenieurskunst']).length!==16)throw Error('Invalid Legacy plan');"
            subprocess.run(['node','-e',check,str(ROOT/'assets/planner-core.js'),str(candidate)],check=True,capture_output=True,text=True)
        temp=path.with_suffix('.json.tmp');temp.write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(path)
        print('Planner data checked:',new['generated'],new['version'])
    except Exception as exc:
        if not args.keep_on_error: raise
        print('Planner source update failed; keeping previous snapshot:',type(exc).__name__)

if __name__=='__main__': main()
