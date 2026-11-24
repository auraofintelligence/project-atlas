import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const root=new URL("../",import.meta.url);
const load=async path=>JSON.parse(await readFile(new URL(path,root),"utf8"));
const atlas=await load("data/projects.json"), external=await load("data/external-projects.json");
const names=new Set(atlas.projects.map(p=>p.name.toLowerCase()));
const urls=new Set();
assert.equal(external.schemaVersion,1);
for(const p of external.projects){
  assert.match(p.name,/^[a-z0-9-]+$/);
  assert.ok(!names.has(p.name)); names.add(p.name);
  assert.equal(p.repositoryUrl,null);
  assert.equal(new URL(p.publicPage).protocol,"https:");
  assert.ok(!urls.has(p.publicPage));urls.add(p.publicPage);
  assert.ok(p.title&&p.description&&p.lifecycle?.status);
  for(const r of p.relatedRepositories||[])assert.ok(atlas.projects.some(a=>a.name===r.name));
  const svg=await readFile(new URL("assets/external-qr/"+p.name+".svg",root),"utf8");
  assert.ok(svg.includes('data-project-atlas-target="'+p.publicPage+'"'));
}
for(const [name,url] of [["straddie-noticeboard-cloudflare","https://straddie-noticeboard-cloudflare.auraofintelligence.workers.dev/"],["PLFC-members-club","https://plfc-clubhouse.auraofintelligence.workers.dev/"]]){
  const p=atlas.projects.find(p=>p.name===name);
  assert.equal(p.publicPage,url);
  const svg=await readFile(new URL("assets/qr/"+name.toLowerCase()+".svg",root),"utf8");
  assert.ok(svg.includes('data-project-atlas-target="'+url+'"'));
}
console.log("PASS: standalone websites, related repository references and deployed project QR targets.");
