"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const source=fs.readFileSync("scripts/check_livnavi_public.cjs","utf8");
function checker(runs,jobs){
 const urls=[];
 const context={
  process:{env:{GITHUB_TOKEN:"test",GITHUB_REPOSITORY:"owner/repo"}},
  Date,AbortSignal,console:{log(){}},
  fetch:async url=>{
   urls.push(url);
   return {ok:true,json:async()=>url.includes("/jobs?")?{jobs}:{workflow_runs:runs}};
  }
 };
 const fn=vm.runInNewContext(source.slice(source.indexOf("async function officialCheck("),source.indexOf("async function liveCheck("))+"; officialCheck",context);
 return {fn,urls};
}
function run(ageHours=0){
 return {id:1,status:"completed",created_at:new Date(Date.now()-ageHours*3600000).toISOString(),html_url:"https://example.test/run"};
}
test("a successful collector is healthy even when the separate publish job failed",async()=>{
 const {fn,urls}=checker([{...run(),conclusion:"failure"}],[{name:"update",conclusion:"success"}]);
 await fn();
 assert.ok(urls[0].includes("event=schedule"));
});
test("weekly original PDF verification uses its actual verify job and freshness window",async()=>{
 const {fn,urls}=checker([run(8*24)],[{name:"verify",conclusion:"success"}]);
 await fn("verify-kaigo-explainers.yml","verify",9*24);
 assert.ok(urls[0].includes("verify-kaigo-explainers.yml/runs?event=schedule"));
});
test("missing daily collection cannot be hidden by old successful runs",async()=>{
 const {fn}=checker([run(49)],[{name:"collect",conclusion:"success"}]);
 await assert.rejects(fn("collect-kaigo-documents.yml","collect",48),/No completed scheduled run/);
});
test("failed source extraction is an anomaly",async()=>{
 const {fn}=checker([run()],[{name:"read-and-publish",conclusion:"failure"}]);
 await assert.rejects(fn("build-kaigo-pdf-evidence.yml","read-and-publish",48),/did not succeed/);
});
