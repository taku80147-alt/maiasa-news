#!/usr/bin/env node
"use strict";
/**
 * Real Chromium smoke tests for the approved smartphone UI.
 * Never edits the app. Any failure blocks the mobile QA workflow.
 */
const {chromium} = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const BASE = "http://127.0.0.1:8765/kaigo-navi2027-preview/";
const widths = [320, 360, 390, 430];
const release = JSON.parse(fs.readFileSync("kaigo-navi2027-preview/data/explainers-verified.json","utf8"));
const autoSales = JSON.parse(fs.readFileSync("kaigo-navi2027-preview/data/sales-guides.json","utf8"));
const four = ["n-pay-269-gh","n-pay-269-sm","n-pay-269-nm","n-pay-269-dn"];

async function noHorizontalOverflow(page, stage, width) {
  const metric = await page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    return {viewport: window.innerWidth, doc: doc.scrollWidth, body:body.scrollWidth};
  });
  assert.ok(metric.doc <= metric.viewport + 1 && metric.body <= metric.viewport + 1,
    `${width}px: horizontal overflow at ${stage}: ${JSON.stringify(metric)}`);
  const clipped=await page.evaluate(()=>[...document.querySelectorAll(".pane.current .card,.pane.current .feature,.pane.current .news,.pane.current .hero,.bottom button")].filter(el=>{
    const r=el.getBoundingClientRect();return r.width>0&&(r.left < -1 || r.right > innerWidth+1);
  }).map(el=>el.className));
  assert.deepEqual(clipped,[],`${width}px: clipped cards/navigation at ${stage}`);
}

async function main() {
  fs.mkdirSync("kaigo-qa-screenshots", {recursive:true});
  const browser = await chromium.launch({headless:true,args:["--no-sandbox"]});
  try {
    for(const width of widths) {
      const page = await browser.newPage({viewport:{width,height:844},deviceScaleFactor:1});
      const errors=[];
      page.on("pageerror",error=>errors.push(error.message));
      const r=await page.goto(BASE,{waitUntil:"domcontentloaded",timeout:30000});
      assert.equal(r.status(),200);
      await page.waitForFunction(()=>document.querySelectorAll("#homeNews [data-id]").length>=1);
      await page.waitForLoadState("networkidle");
      await page.evaluate(()=>document.fonts.ready);
      await noHorizontalOverflow(page,"homepage",width);
      // Home retains required visual concepts and navigation.
      assert.equal(await page.locator("#homeNews .news").count(),5,"home shows five compact headlines");
      assert.equal(await page.locator("#homeNews img").count(),0,"headlines have no thumbnails");
      assert.equal(await page.locator("#featureGrid,.daily-grid,.recs").count(),0,"removed home sections must stay removed");
      assert.equal(await page.locator("#dailyTip").count(),1);
      assert.match(await page.locator("#dailyTip").getAttribute("data-date"),/^20\d{2}-\d{2}-\d{2}$/);
      assert.ok((await page.locator("#dailyTip .today-title").innerText()).length>2);
      assert.ok((await page.locator("#dailyTip .today-quote").innerText()).length>10);
      assert.deepEqual(await page.locator(".bottom button").allTextContents(),["⌂ニュース","⌕検索","♡保存"]);
      await page.screenshot({path:path.join("kaigo-qa-screenshots",`home_${width}.png`),fullPage:true});
      // Compare adopted static visual regions to the unchanged previous source.
      if(process.env.KAIGO_BASELINE_URL) {
        const baseline = await browser.newPage({viewport:{width,height:844},deviceScaleFactor:1});
        await baseline.goto(process.env.KAIGO_BASELINE_URL,{waitUntil:"networkidle"});
        await baseline.evaluate(()=>document.fonts.ready);
        console.log("Visual document geometry", width, JSON.stringify(await page.evaluate(()=>({height:document.body.scrollHeight}))), JSON.stringify(await baseline.evaluate(()=>({height:document.body.scrollHeight}))));
        // A fixed footer must not cover the region being compared.
        // Rounded corners include the page gradient, which depends on the intended shorter home height.
        // Compare the unchanged component on the same backdrop; full-home shots remain unmodified.
        const comparisonStyle=".bottom{visibility:hidden!important}body{background:#fff!important}";
        const hideFooter=await page.addStyleTag({content:comparisonStyle});
        await baseline.addStyleTag({content:comparisonStyle});
        for(const selector of [".hero",".livnavi-wordmark"]) {
          const label=selector.replace(/[^a-zA-Z0-9]/g, "");
          const before=await baseline.locator(selector).screenshot({path:path.join("kaigo-qa-screenshots",`${width}_${label}_before.png`)});
          const after=await page.locator(selector).screenshot({path:path.join("kaigo-qa-screenshots",`${width}_${label}_after.png`)});
          console.log("Visual region",width,selector,JSON.stringify({before:await baseline.locator(selector).boundingBox(),after:await page.locator(selector).boundingBox()}));
          assert.ok(before.equals(after), `${width}px: adopted design changed at ${selector}`);
        }
        await hideFooter.evaluate(el=>el.remove());
        await baseline.close();
      }
      // Parent Oct 9 overview: all four newly reviewed services must be navigable.
      await page.locator('.more-news').click();
      await page.locator('#viewbody [data-id="n-pay-269"]').first().click();
      for(const id of four) {
        const el=page.locator('#viewbody [data-id="'+id+'"]');
        assert.equal(await el.count(),1,`missing overview link to ${id}`);
      }
      await noHorizontalOverflow(page,"overview",width);
      // Verify 3-level reading controls and back navigation, on two representative topics.
      for(const id of [four[0],four[3]]) {
        await page.locator('#viewbody [data-id="'+id+'"]').click();
        await page.locator('.reform-reader').waitFor({state:"visible",timeout:12000});
        for(const section of ["summary","changes","audience","impact","timing","sources"]){
          const panel=page.locator('[data-reader-section="'+section+'"]');
          assert.ok(await panel.isVisible(),`${id}: missing ${section}`);
          assert.ok((await panel.innerText()).trim().length>8);
        }
        await noHorizontalOverflow(page,`${id} detail`,width);
        await page.locator("#back").click();
      }
      await page.screenshot({path:path.join("kaigo-qa-screenshots",`overview_${width}.png`),fullPage:true});
      // Every reviewed article, including current-system lessons, must load from a share link.
      for(const article of release.articles) {
        await page.goto(BASE+"#article="+article.id,{waitUntil:"networkidle"});
        await page.locator(".reform-reader").waitFor();
        assert.ok((await page.locator(".exp-safe").innerText()).includes(article.status));
        for(const section of ["summary","changes","audience","impact","timing","sources"]){
          const panel=page.locator('[data-reader-section="'+section+'"]');
          assert.ok(await panel.isVisible());
          assert.ok((await panel.innerText()).length>8);
        }
        if(article.id==="n-notice-vol-1549"){
          assert.ok((await page.locator('[data-reader-section="timing"]').innerText()).includes("2027-02-01"));
          assert.ok((await page.locator('[data-reader-section="changes"]').innerText()).includes("給付対象外"));
          // Inline blue PDF page references must be real, tappable links, including in an in-app browser.
          const sourceLinks=page.locator('[data-reader-section="changes"] a.exp-cite');
          assert.equal(await sourceLinks.count(),article.explain.length,"every explanation has an actionable source");
          for(let i=0;i<article.explain.length;i++){
            const expectedPage=article.explain[i].source.normalize("NFKC").match(/PDF\s*([1-9]\d*)/i);
            assert.equal(await sourceLinks.nth(i).getAttribute("href"),article.source_pdf+(expectedPage?"#page="+Number(expectedPage[1]):""));
            assert.equal(await sourceLinks.nth(i).getAttribute("target"),"_self");
          }
          await page.screenshot({path:path.join("kaigo-qa-screenshots",`notice1549_${width}.png`),fullPage:true});
          // Stub only the external PDF response; prove the tap navigates this tab rather than opening a popup.
          const pdfPattern="https://www.mhlw.go.jp/content/001762862.pdf*";
          await page.route(pdfPattern,route=>route.fulfill({contentType:"text/html",body:"<!doctype html><title>Official PDF navigation fixture</title><p>PDF navigation reached</p>"}));
          const tabsBefore=page.context().pages().length;
          await sourceLinks.first().click();
          await page.waitForURL(article.source_pdf+"#page=3");
          assert.equal(page.context().pages().length,tabsBefore,"PDF tap must not require a new window");
          await page.goBack({waitUntil:"networkidle"});
          await page.locator(".reform-reader").waitFor();
          await page.unroute(pdfPattern);
        }
        await noHorizontalOverflow(page,article.id,width);
      }
      // Favorites survive reload; full-text search normalizes full-width digits.
      await page.goto(BASE+"#article=l-equipment-choice",{waitUntil:"networkidle"});
      await page.locator('#viewbody [data-save="l-equipment-choice"]').click();
      await page.reload({waitUntil:"networkidle"});
      assert.ok((await page.locator('#viewbody [data-save="l-equipment-choice"]').innerText()).includes("保存済み"));
      await page.locator('.bottom [data-go="favorites"]').click();
      assert.equal(await page.locator('#viewbody [data-id="l-equipment-choice"]').count(),1);
      await page.locator('.bottom [data-go="search"]').click();
      await page.locator("#q").fill("歩行車");
      assert.ok(await page.locator('#results [data-id="l-equipment-choice"]').count());
      await page.locator("#q").fill("２割 負担");
      assert.ok(await page.locator('#results [data-id="n-ins-136-burden"]').count());
      await page.locator('#results [data-id="n-ins-136-burden"]').click();
      await page.locator("#back").click();
      assert.equal(await page.locator("#q").inputValue(),"２割 負担");
      await page.locator('.bottom [data-go="home"]').click();
      assert.deepEqual(errors,[],`${width}px browser JavaScript errors: ${errors.join("; ")}`);
      console.log(`PASS ${width}px: home, no horizontal overflow, four linked articles, vertical reader, back navigation`);
      await page.close();
    }
    // Fail closed if release prose is changed without the matching content audit.
    const tampered=await browser.newPage();
    await tampered.route("**/data/explainers-verified.json*",route=>{
      const data=structuredClone(release);
      data.articles.find(a=>a.id==="n-pay-268").one_liner="改定額が決定したという偽の本文";
      return route.fulfill({json:data});
    });
    await tampered.goto(BASE+"#article=n-pay-268",{waitUntil:"networkidle"});
    assert.equal(await tampered.locator(".reform-reader").count(),0,"tampered article must be withheld");
    await tampered.close();
    const offline=await browser.newPage();
    await offline.route("**/data/*",route=>route.abort());
    await offline.goto(BASE,{waitUntil:"networkidle"});
    assert.ok(await offline.locator("#feedWarning").isVisible());
    assert.ok((await offline.locator("#feedWarning").innerText()).includes("最新情報を取得できません"));
    await offline.close();
  } finally {await browser.close()}
}
main().catch(e=>{console.error(e.stack||e);process.exit(1)});


