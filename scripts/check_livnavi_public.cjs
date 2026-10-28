#!/usr/bin/env node
"use strict";
// Compare scheduled MHLW checks, repository feed, actual published feed, and rendered mobile home.
const fs=require("node:fs");
const assert=require("node:assert/strict");
const {chromium}=require("playwright");
const BASE="https://taku80147-alt.github.io/maiasa-news/kaigo-navi2027-preview/";
const source=JSON.parse(fs.readFileSync("kaigo-navi2027-preview/data/latest.json","utf8"));
const sales=JSON.parse(fs.readFileSync("kaigo-navi2027-preview/data/sales-guides.json","utf8"));
const reviewedRelease=JSON.parse(fs.readFileSync("kaigo-navi2027-preview/data/explainers-verified.json","utf8"));
const reviewedIds=new Set(reviewedRelease.articles.map(a=>a.id));
assert.ok(Array.isArray(source.articles)&&source.articles.length>0,"Repository feed is empty");
const first=[...source.articles].filter(a=>/^n-[a-z0-9-]+$/.test(a.id))
 .sort((a,b)=>b.date.localeCompare(a.date)||a.id.localeCompare(b.id))[0];
assert.ok(first,"No eligible official source articles");
function assertNoticeCoverage(inventory,feed){
 assert.equal(inventory.schema_version,1,"Unknown source inventory schema");
 assert.ok(Array.isArray(inventory.documents)&&inventory.documents.length>0,"Missing notice discovery inventory");
 const ids=new Set();
 for(const row of inventory.documents){
  assert.ok(!ids.has(row.id),"Duplicate discovered notice");ids.add(row.id);
  assert.ok(["include","excluded","review_pending"].includes(row.selection)&&row.reason,"Notice missing triage decision");
  if(row.selection==="include")assert.ok(feed.articles.some(a=>a.id===row.id&&a.source_url===row.source_url),"Discovered reform notice missing from feed: "+row.id);
 }
 console.log("NOTICE_COVERAGE_OK",inventory.documents.length,"pending review",inventory.documents.filter(r=>r.selection==="review_pending").length);
}
async function officialCheck(workflow="update-kaigo-reform.yml",jobName="update",hours=48){
 const token=process.env.GITHUB_TOKEN,repo=process.env.GITHUB_REPOSITORY;
 if(!token||!repo)throw Error("GitHub monitoring credentials missing");
 const url="https://api.github.com/repos/"+repo+"/actions/workflows/"+workflow+"/runs?event=schedule&per_page=12";
 const resp=await fetch(url,{headers:{Authorization:"Bearer "+token,Accept:"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"},signal:AbortSignal.timeout(25000)});
 if(!resp.ok)throw Error("Cannot verify MHLW scheduled collector: HTTP "+resp.status);
 const runs=(await resp.json()).workflow_runs||[];
 const recent=runs.filter(r=>Date.now()-Date.parse(r.created_at)<hours*3600000);
 console.log("MHLW_SCHEDULED_RUNS",JSON.stringify(runs.slice(0,8).map(r=>({created_at:r.created_at,status:r.status,conclusion:r.conclusion,event:r.event,url:r.html_url}))));
 const finished=recent.filter(r=>r.status==="completed");
 if(!finished.length)throw Error("No completed scheduled run for "+workflow+" in the past "+hours+" hours");
 // The workflow can fail AFTER successful collection because publication has independent QA.
 // Check the actual update job instead of incorrectly treating failed publish as failed source collection.
 const latest=finished[0];
 const jobsUrl="https://api.github.com/repos/"+repo+"/actions/runs/"+latest.id+"/jobs?per_page=100";
 const jobsResponse=await fetch(jobsUrl,{headers:{Authorization:"Bearer "+token,Accept:"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"},signal:AbortSignal.timeout(25000)});
 if(!jobsResponse.ok)throw Error("Cannot inspect MHLW collection job: HTTP "+jobsResponse.status);
 const jobs=(await jobsResponse.json()).jobs||[];
 const update=jobs.find(j=>j.name===jobName);
 if(!update||update.conclusion!=="success")
  throw Error("Latest "+workflow+" "+jobName+" job did not succeed: "+latest.html_url+" (status="+(update?.conclusion||"missing")+")");
 console.log("MHLW pipeline job healthy:",workflow,jobName,latest.html_url, "publish conclusion:",latest.conclusion);
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
  const publishedGuides=await page.evaluate(async()=>{
   const url=new URL("data/sales-guides.json",location.href);
   url.searchParams.set("monitor",String(Date.now()));
   const response=await fetch(url,{cache:"no-store"});
   if(!response.ok)throw Error("Live sales guidance: HTTP "+response.status);
   return response.json();
  });
  assert.deepEqual(publishedGuides.guides,sales.guides,"Published sales guides differ from GitHub main");
  const publishedReviewed=await page.evaluate(async()=>{
   const u=new URL("data/explainers-verified.json",location.href);
   u.searchParams.set("monitor",String(Date.now()));
   const response=await fetch(u,{cache:"no-store"});
   if(!response.ok)throw Error("Reviewed explanations HTTP "+response.status);
   return response.json();
  });
  assert.deepEqual(publishedReviewed.articles,reviewedRelease.articles,
    "Published full explanations differ from verified articles on GitHub main");
  assert.deepEqual(publishedReviewed.source_audits,reviewedRelease.source_audits,
    "Published source audits differ from the verified original PDF checks");

  const inventory=JSON.parse(fs.readFileSync("kaigo-navi2027-preview/data/source-inventory.json","utf8"));
  assertNoticeCoverage(inventory,source);
  const publishedInventory=await page.evaluate(async()=>{
   const response=await fetch(new URL("data/source-inventory.json?monitor="+Date.now(),location.href),{cache:"no-store"});
   if(!response.ok)throw Error("Notice inventory HTTP "+response.status);
   return response.json();
  });
  assert.deepEqual(publishedInventory,inventory,"Published notice inventory differs from GitHub main");
  assertNoticeCoverage(publishedInventory,publicFeed);

  const localEvidence="kaigo-navi2027-preview/data/pdf-evidence.json";
  if(fs.existsSync(localEvidence)){
   const expected=JSON.parse(fs.readFileSync(localEvidence,"utf8"));
   const published=await page.evaluate(async()=>{
    const url=new URL("data/pdf-evidence.json",location.href);
    url.searchParams.set("monitor",String(Date.now()));
    const response=await fetch(url,{cache:"no-store"});
    if(!response.ok)throw Error("PDF evidence HTTP "+response.status);
    return response.json();
   });
   assert.deepEqual(published.articles,expected.articles,
     "Published source-PDF evidence differs from repository");
   console.log("PDF_EVIDENCE_PUBLICATION_OK",expected.articles.length);
  }

  await page.waitForFunction(id=>document.querySelector("#homeNews .news[data-id]")?.dataset.id===id,first.id,{timeout:15000});
  const card=page.locator("#homeNews .news").first();
  assert.equal(await card.getAttribute("data-id"),first.id,"Displayed first article is old");
  assert.ok((await card.innerText()).includes(first.title),"Displayed headline is stale");
  const reviewedItem=reviewedRelease.articles.find(r=>r.id===first.id);
  if(reviewedItem){
    await page.locator("#homeNews .news").first().click();
    await page.locator(".reform-reader").waitFor({state:"visible",timeout:16000});
    for(const section of ["summary","changes","audience","impact","timing","sources"]){
      const panel=page.locator('[data-reader-section="'+section+'"]');
      assert.ok(await panel.isVisible(),"Reader section not visible: "+section);
      assert.ok((await panel.innerText()).length>8,"Reader section unexpectedly blank: "+section);
    }
    const text=await page.locator(".exp-card").innerText();
    assert.ok(text.includes(reviewedItem.one_liner),"Reviewed explanation is not rendered for latest article");
    console.log("LIVNAVI_REVIEWED_READER_OK",reviewedItem.id,reviewedRelease.articles.length);
  }
  assert.equal(await page.locator("#homeNews .news").count(),5,"Expected 5 visible homepage news cards");
  assert.deepEqual(errors,[],"Homepage JavaScript errors");
  console.log("LIVNAVI_OK",JSON.stringify({latest_date:first.date,first_id:first.id,articles:publicFeed.articles.length,verified_on:publicFeed.verified_on}));
 }finally{await page.close()}
}
(async()=>{
 const errors=[];
 for(const [workflow,jobName,hours] of [
  ["update-kaigo-reform.yml","update",48],
  ["collect-kaigo-documents.yml","collect",48],
  ["build-kaigo-pdf-evidence.yml","read-and-publish",48],
  ["verify-kaigo-explainers.yml","verify",9*24]
 ]){
  try{await officialCheck(workflow,jobName,hours)}catch(e){errors.push("OFFICIAL_PIPELINE "+workflow+": "+(e.stack||e))}
 }
 const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
 try{
  for(let n=1;n<=3;n++){
   try{await liveCheck(browser);break}
   catch(e){console.error("Live check "+n+"/3:",e.stack||e);if(n===3)errors.push("PUBLIC_SITE: "+(e.stack||e));else await new Promise(r=>setTimeout(r,20000))}
  }
 }finally{await browser.close()}
 if(errors.length)throw Error(errors.join("\\n\\n"));
 console.log("LIVNAVI_ALL_CHECKS_PASSED");
})().catch(e=>{console.error("LIVNAVI_MONITOR_FAILED",e.stack||e);process.exitCode=1});


