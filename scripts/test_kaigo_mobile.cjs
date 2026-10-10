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
const four = ["n-pay-269-gh","n-pay-269-sm","n-pay-269-nm","n-pay-269-dn"];

async function noHorizontalOverflow(page, stage, width) {
  const metric = await page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    return {viewport: window.innerWidth, doc: doc.scrollWidth, body:body.scrollWidth};
  });
  assert.ok(metric.doc <= metric.viewport + 1 && metric.body <= metric.viewport + 1,
    `${width}px: horizontal overflow at ${stage}: ${JSON.stringify(metric)}`);
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
      await noHorizontalOverflow(page,"homepage",width);
      // Home retains required visual concepts and navigation.
      assert.ok(await page.locator("#homeNews .news").count()>=3,"home must show 3 news cards");
      assert.ok(await page.locator(".bottom button").count()>=3,"bottom navigation missing");
      await page.screenshot({path:path.join("kaigo-qa-screenshots",`home_${width}.png`),fullPage:true});
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
      await page.screenshot({path:path.join("kaigo-qa-screenshots",`article_${width}.png`),fullPage:true});
      assert.deepEqual(errors,[],`${width}px browser JavaScript errors: ${errors.join("; ")}`);
      console.log(`PASS ${width}px: home, no horizontal overflow, four linked articles, 3 reading tabs, back navigation`);
      await page.close();
    }
  } finally {await browser.close()}
}
main().catch(e=>{console.error(e.stack||e);process.exit(1)});
