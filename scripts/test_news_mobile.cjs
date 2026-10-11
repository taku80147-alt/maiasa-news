const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const edition=JSON.parse(fs.readFileSync('data/news.json','utf8'));
const checkedAt=new Date(edition.updated_at);
const base='http://127.0.0.1:8765/';
(async()=>{
  fs.mkdirSync('news-qa-screenshots',{recursive:true});
  const browser=await chromium.launch();
  try {
    for(const width of [320,360,390,430,1280]) {
      const page=await browser.newPage({viewport:{width,height:900},timezoneId:'Asia/Tokyo'});
      // Validate each saved edition at its check time, then separately test expiration.
      // An old news file must never prevent an unrelated care-app release.
      await page.clock.setFixedTime(checkedAt);
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      await page.goto(base);
      await page.waitForFunction(()=>document.querySelector('#updated').textContent!=='確認中');
      assert.equal(await page.locator('#tabs button').count(),8);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      assert.equal(await page.locator('button label').count(),0);
      assert.equal(await page.locator('.reading-links a').count(),4);
      assert.equal(await page.locator('.care-link').getAttribute('href'),'kaigo-navi2027-preview/');
      assert(!await page.locator('#tabs').evaluate(el=>el.scrollWidth>el.clientWidth));
      const total=await page.locator('#news-list .card').count();
      assert.equal(await page.locator('#important-list .card').count(),Math.min(3,edition.important_ids.length));
      await page.screenshot({path:`news-qa-screenshots/home-${width}.png`,fullPage:true});
      if(total) {
        const detail=page.locator('#news-list .card-button').filter({hasText:'詳しく読む'}).first();
        if(await detail.count()) {
          await detail.click();await page.locator('dialog[open]').waitFor();
          assert((await page.locator('#detail .content-summary').textContent()).length>40);
          assert(await page.locator('#detail .source-link').getAttribute('href'));
          assert(await page.evaluate(()=>document.querySelector('dialog').scrollWidth<=document.querySelector('dialog').clientWidth));
          await page.screenshot({path:`news-qa-screenshots/detail-${width}.png`});
          await page.keyboard.press('Escape');assert.equal(await page.locator('dialog[open]').count(),0);
        }
        await page.locator('[data-category="world"].tab').click();
        assert(await page.locator('#news-list .card').evaluateAll(rows=>rows.every(r=>r.dataset.category==='world')));
        await page.locator('[data-category="national"].tab').click();
        await page.locator('#empty').waitFor({state:'visible'});
        await page.locator('#reset-filter').click();
        assert.equal(await page.locator('#news-list .card').count(),total);
        const checkbox=page.locator('#news-list .select-row input:enabled').first();
        if(await checkbox.count()) {
          await checkbox.check();assert.equal(await page.locator('#selection-count').textContent(),'1');
          await page.locator('#selection-bar').waitFor({state:'visible'});
          const popupPromise=page.waitForEvent('popup');await page.locator('#make-pdf').click();
          const popup=await popupPromise;await popup.waitForLoadState();
          assert.equal(await popup.title(),'毎朝ニュース');
          assert(await popup.locator('article').count()>0);
          assert((await popup.locator('body').textContent()).includes('利用条件'));
          await popup.close();await checkbox.uncheck();
          await page.locator('#selection-bar').waitFor({state:'hidden'});
        }
      } else {
        await page.locator('#empty').waitFor({state:'visible'});
      }
      assert.deepEqual(errors,[]);await page.close();
      console.log(`${width}px: edition layout, available articles, tabs, sources, care link and eligible PDF passed`);
    }
    const broken=await browser.newPage({viewport:{width:320,height:900}});
    await broken.route('**/data/news.json*',r=>r.fulfill({status:500,body:'unavailable'}));
    await broken.goto(base);await broken.getByText('紙面を取得できません').waitFor();
    assert.equal(await broken.locator('.reading-links a').count(),4);
    await broken.screenshot({path:'news-qa-screenshots/unavailable-320.png'});await broken.close();
    const invalid=await browser.newPage({viewport:{width:390,height:900}});
    await invalid.clock.setFixedTime(checkedAt);
    const day=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo'}).format(checkedAt);
    const good=edition.items[0]||{id:'qa-fixture',title:'表示検査用の公式情報',summary:'表示検査にのみ使用する文章です。',source_id:'sendai',source:'仙台市',url:'https://www.city.sendai.jp/',category:'local',published:day,primary:true,source_type:'official',verified_source:true,link_only:true,status:'見出し'};
    const corrupt={...edition,items:[good,{...good,id:'evil',url:'javascript:alert(1)'},{...good,id:'bad-date',published:'2026-02-30'},{...good,id:'old-care',category:'care'},{...good,id:'host-spoof',url:'https://www.mofa.go.jp.evil.invalid/'},{...good,id:'expired',published:'1900-01-01'},{...good,id:'future',published:'9999-01-01'},good],important_ids:[good.id]};
    await invalid.route('**/data/news.json*',r=>r.fulfill({json:corrupt}));
    await invalid.goto(base);await invalid.waitForFunction(()=>document.querySelectorAll('#news-list .card').length===1);await invalid.close();
    const expired=await browser.newPage({viewport:{width:320,height:900}});
    await expired.clock.setFixedTime(new Date(checkedAt.getTime()+9*86400000));
    await expired.goto(base);await expired.locator('#source-warning').waitFor({state:'visible'});
    await expired.locator('#empty').waitFor({state:'visible'});
    assert.equal(await expired.locator('#news-list .card').count(),0);
    assert.equal(await expired.locator('.reading-links a').count(),4);await expired.close();
    const empty=await browser.newPage({viewport:{width:320,height:900}});
    await empty.clock.setFixedTime(checkedAt);
    await empty.route('**/data/news.json*',r=>r.fulfill({json:{...edition,items:[],important_ids:[]}}));
    await empty.goto(base);await empty.locator('#empty').waitFor({state:'visible'});
    assert.equal(await empty.locator('#news-list .card').count(),0);await empty.close();
    console.log('Unavailable, malformed, duplicate, expired, future and empty data: safe fallback passed');
  } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
