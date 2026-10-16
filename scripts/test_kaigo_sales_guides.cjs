#!/usr/bin/env node
"use strict";
const fs=require("node:fs");
const assert=require("node:assert/strict");
const {buildGuides}=require("./build_kaigo_sales_guides.cjs");
const root="kaigo-navi2027-preview/data/";
const feed=JSON.parse(fs.readFileSync(root+"latest.json","utf8"));
const actual=JSON.parse(fs.readFileSync(root+"sales-guides.json","utf8"));
const expected=buildGuides(feed);
assert.deepEqual(actual,expected,"Sales guides must be regenerated from current official feed");
assert.ok(actual.guides.length>=3);
const ids=actual.guides.map(g=>g.id);
assert.equal(ids.length,new Set(ids).size,"Duplicate auto-sales IDs");
for(const g of actual.guides){
 const a=feed.articles.find(x=>x.id===g.id);
 assert.ok(a,"Guide without official article");
 assert.equal(g.date,a.date);
 assert.equal(g.source_url,a.source_url);
 assert.ok(g.source_url.startsWith("https://www.mhlw.go.jp/"));
 assert.ok(g.stage.includes("精読")&&g.stage.includes("未実施"),"Must label source scope");
 assert.ok(g.check_first.includes("議題"),"Must distinguish agenda from approved policy");
 assert.ok(g.topics.length>0);
 for(const topic of g.topics){
  assert.ok(topic.question.endsWith("？")&&topic.question.length>=13);
  assert.ok(topic.next.length>=13);
 }
 assert.ok(!g.intro.includes("正式決定した内容"),"Do not imply adopted law");
}
const top=actual.guides.find(g=>g.id==="n-pay-270");
if(top){
 for(const name of ["通所介護","通所リハビリテーション","短期入所生活介護"])assert.ok(top.topics.some(x=>x.label===name));
}
assert.ok(!actual.guides.some(g=>g.id.startsWith("n-law")),"Published laws require an expert-reviewed explanation");
console.log("PASS sales guidance coverage",actual.guides.length,"articles; topics for latest:",top?.topics.map(x=>x.label).join(","));
