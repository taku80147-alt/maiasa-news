#!/usr/bin/env node
"use strict";
// Compare scheduled MHLW checks, repository feed, actual published feed, and rendered mobile home.
const fs=require("node:fs");
const assert=require("node:assert/strict");
const {chromium}=require("playwright");
const BASE="https://taku80147-alt.github.io/maiasa-news/kaigo-navi2027-preview/";
const source=JSON.parse(fs.readFileSync("kaigo-navi2027-preview/data/latest.json","utf8"));
assert.ok(Array.isArray(source.articles)&&source.articles.length>0,"Repository feed is empty");
const first=[...source.articles].filter(a=>/^n-[a-z0-9-]+$/.test(a.id))
 .sort((a,b)=>b.date.localeCompare(a.date)||a.id.localeCompare(b.id))[0];
assert.ok(first,"No eligible official source articles");
async function officialCheck(){
 const token=process.env.GITHUB_TOKEN,repo=process.env.GITHUB_REPOSITORY;
 if(!token||!repo)throw Error("GitHub monitoring credentials missing");
 const url="https://api.github.com/repos/"+repo+"/actions/workflows/update-kaigo-reform.yml/runs?event=schedule&per_page=12";
 const resp=await fetch(url,{headers:{Authorization:"Bearer "+token,Accept:"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"},signal:AbortSignal.timeout(25000)});
 if(!resp.ok)throw Error("Cannot verify MHLW scheduled collector: HTTP "+resp.status);
 const runs=(await resp.json()).workflow_runs||[];
 const recent=runs.filter(r=>Date.now()-Date.parse(r.created_at)<48*3600000);
 if(!recent.some(r=>r.conclusion==="success"))throw Error("No successful MHLW scheduled collector in the past 48 hours");
 if(runs[0]?.conclusion==="failure"&&Date.now()-Date.parse(runs[0].created_at)<36*3600000)
  throw Error("Newest MHLW collector failed: "+runs[0].html_url);
 console.log("MHLW collector healthy:",recent.find(r=>r.conclusion==="success").html_url);
}
async function liveCheck(browser){
 const page=await browser.newPage({viewport:{width:390,height:844},locale:"ja-JP"});
 const errors=[];page.on("pageerror",e=>errors.push(e.message));
 try{
  const pageResponse=await page.goto(BASE+"?monitor="+Date.now(),{waitUntil:"networkidle",timeout:45000});
  assert.equal(pageResponse?.status(),200,"Live page request failed");
  const publicFeed=await page.evaluate(async()=>{
   const url=new URL("data/latest.json",location.href);
   url.searchParams.set("monitor",String(Date.now()));
   const res=await fetch(url,{cache:"no-store"});
   if(!res.ok)throw Error("Live data error "+res.status);
   return res.json();
  });
  assert.deepEqual(publicFeed.articles,source.articles,"Published article feed differs from GitHub main");
  assert.equal(publicFeed.verified_on,source.verified_on,"Published metadata differs from GitHub main");
  await page.waitForFunction(id=>document.querySelector("#homeNews .news[data-id]")?.dataset.id===id,first.id,{timeout:15000});
  const card=page.locator("#homeNews .news").first();
  assert.equal(await card.getAttribute("data-id"),first.id,"Displayed first article is old");
  assert.ok((await card.innerText()).includes(first.title),"Displayed headline is stale");
  assert.equal(await page.locator("#homeNews .news").count(),3,"Expected 3 visible homepage news cards");
  assert.deepEqual(errors,[],"Homepage JavaScript errors");
  console.log("LIVNAVI_OK",JSON.stringify({latest_date:first.date,first_id:first.id,articles:publicFeed.articles.length,verified_on:publicFeed.verified_on}));
 }finally{await page.close()}
}
(async()=>{
 await officialCheck();
 const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
 try{
  for(let n=1;n<=3;n++){
   try{await liveCheck(browser);return}
   catch(e){console.error("Live check "+n+"/3:",e.stack||e);if(n===3)throw e;await new Promise(r=>setTimeout(r,20000))}
  }
 }finally{await browser.close()}
})().catch(e=>{console.error("LIVNAVI_MONITOR_FAILED",e.stack||e);process.exitCode=1});
