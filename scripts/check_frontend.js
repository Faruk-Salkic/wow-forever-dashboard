const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
for(const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) if(match[1].trim()) new vm.Script(match[1]);
for(const f of fs.readdirSync(path.join(root,'assets')).filter(f=>f.endsWith('.js'))) new vm.Script(fs.readFileSync(path.join(root,'assets',f),'utf8'),{filename:f});
for(const match of html.matchAll(/(?:src|href)="((?:assets|data)\/[^"?]+)(?:\?[^\"]*)?"/g)) if(!fs.existsSync(path.join(root,match[1]))) throw Error('Missing asset: '+match[1]);
console.log('Frontend syntax and local assets OK');
