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
      assert.ok(await page.locator("#homeNews .news").count()>=3,"home must show 3 news cards");
      assert.ok(await page.locator(".bottom button").count()>=3,"bottom navigation missing");
      await page.screenshot({path:path.join("kaigo-qa-screenshots",`home_${width}.png`),fullPage:true});
      // Compare adopted static visual regions to the unchanged previous source.
      if(process.env.KAIGO_BASELINE_URL) {
        const baseline = await browser.newPage({viewport:{width,height:844},deviceScaleFactor:1});
        await baseline.goto(process.env.KAIGO_BASELINE_URL,{waitUntil:"networkidle"});
        // A fixed footer must not cover the region being compared.
        const hideFooter=await page.addStyleTag({content:".bottom{visibility:hidden!important}"});
        await baseline.addStyleTag({content:".bottom{visibility:hidden!important}"});
        for(const selector of [".hero","#featureGrid",".daily-grid"]) {
          const label=selector.replace(/[^a-zA-Z0-9]/g, "");
          const before=await baseline.locator(selector).screenshot({path:path.join("kaigo-qa-screenshots",`${width}_${label}_before.png`)});
          const after=await page.locator(selector).screenshot({path:path.join("kaigo-qa-screenshots",`${width}_${label}_after.png`)});
          console.log("Visual region",width,selector,JSON.stringify({before:await baseline.locator(selector).boundingBox(),after:await page.locator(selector).boundingBox()}));
          assert.ok(before.equals(after), `${width}px: adopted design changed at ${selector}`);
        }
        await hideFooter.evaluate(el=>el.remove());
        await baseline.close();
      }
      // A newly added official meeting must have a visible, explicitly provisional sales guide.
      const homeFirstId=await page.locator("#homeNews .news").first().getAttribute("data-id");
      const autoGuide=autoSales.guides.find(g=>g.id===homeFirstId);
      if(autoGuide && !release.articles.some(a=>a.id===homeFirstId)){
        await page.locator("#homeNews .news").first().click();
        await page.locator(".sales-auto").waitFor({state:"visible",timeout:14000});
        const guideText=await page.locator(".sales-auto").innerText();
        assert.ok(guideText.includes(autoGuide.topics[0].question),
          "Latest article must show its concrete sales question");
        assert.ok(guideText.includes("資料本文の精読"),"Automatic guide must disclose its limitations");
        await page.locator(".bottom [data-go='home']").click();
      }
      // Parent Oct 9 overview: all four newly reviewed services must be navigable.
      await page.locator('.bottom [data-go="news"]').first().click();
      await page.locator('#viewbody [data-id="n-pay-269"]').first().click();
      for(const id of four) {
        const el=page.locator('#viewbody [data-id="'+id+'"]');
        assert.equal(await el.count(),1,`missing overview link to ${id}`);
      }
      await noHorizontalOverflow(page,"overview",width);
      // Verify 3-level reading controls and back navigation, on two representative topics.
      for(const id of [four[0],four[3]]) {
        await page.locator('#viewbody [data-id="'+id+'"]').click();
        await page.locator('.exp-tabs').waitFor({state:"visible",timeout:12000});
        for (const tab of ["quick","deep","sales"]) {
          await page.locator('[data-exp-tab="'+tab+'"]').click();
          const panel=page.locator('[data-exp-panel="'+tab+'"]');
          assert.equal(await panel.isVisible(),true,`${id} tab ${tab} not visible`);
          assert.ok((await panel.innerText()).trim().length>=40,`empty panel: ${id}/${tab}`);
        }
        await noHorizontalOverflow(page,`${id} detail`,width);
        await page.locator("#back").click();
      }
      await page.screenshot({path:path.join("kaigo-qa-screenshots",`overview_${width}.png`),fullPage:true});
      // Every reviewed article, including current-system lessons, must load from a share link.
      for(const article of release.articles) {
        await page.goto(BASE+"#article="+article.id,{waitUntil:"networkidle"});
        await page.locator(".exp-tabs").waitFor();
        assert.ok((await page.locator(".exp-safe").innerText()).includes(article.status));
        for(const tab of ["quick","deep","sales"]) {
          await page.locator('[data-exp-tab="'+tab+'"]').click();
          assert.ok((await page.locator('[data-exp-panel="'+tab+'"]').innerText()).length>40);
          if(["n-ins-136-burden","l-equipment-choice","n-law51-overview"].includes(article.id) && ["deep","sales"].includes(tab))
            await page.screenshot({path:path.join("kaigo-qa-screenshots",`${article.id}_${tab}_${width}.png`),fullPage:true});
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
      await page.locator('.bottom [data-go="ai"]').click();
      await page.locator("#q").fill("歩行車");
      assert.ok(await page.locator('#results [data-id="l-equipment-choice"]').count());
      await page.locator("#q").fill("２割 負担");
      assert.ok(await page.locator('#results [data-id="n-ins-136-burden"]').count());
      await page.locator('#results [data-id="n-ins-136-burden"]').click();
      await page.locator("#back").click();
      assert.equal(await page.locator("#q").inputValue(),"２割 負担");
      await page.locator('.bottom [data-go="home"]').click();
      await page.locator('[data-go="today"]').click();
      assert.ok(await page.locator('#viewbody [data-id="l-equipment-choice"]').count());
      // The colored feature cards lead to real 3-level explanations.
      await page.locator('.bottom [data-go="home"]').click();
      for(const id of ["n-pay-268","n-ins-136-burden","n-pay-259"]) {
        await page.locator('#featureGrid [data-id="'+id+'"]').click();
        await page.locator(".exp-tabs").waitFor();
        await page.locator('.bottom [data-go="home"]').click();
      }
      assert.deepEqual(errors,[],`${width}px browser JavaScript errors: ${errors.join("; ")}`);
      console.log(`PASS ${width}px: home, no horizontal overflow, four linked articles, 3 reading tabs, back navigation`);
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
    assert.equal(await tampered.locator(".exp-tabs").count(),0,"tampered article must be withheld");
    await tampered.close();
    const offline=await browser.newPage();
    await offline.route("**/data/*",route=>route.abort());
    await offline.goto(BASE,{waitUntil:"networkidle"});
    assert.ok((await offline.locator(".updatetag").innerText()).includes("取得に失敗"));
    await offline.close();
  } finally {await browser.close()}
}
main().catch(e=>{console.error(e.stack||e);process.exit(1)});

