const test = require('node:test');
const assert = require('node:assert/strict');
const {select} = require('../kaigo-navi2027-preview/daily-tip.js');

test('JST midnight changes the date and topic, independently of the server timezone', () => {
  const before = select(new Date('2026-10-28T14:59:59Z'));
  const after = select(new Date('2026-10-28T15:00:00Z'));
  assert.equal(before.date, '2026-10-28');
  assert.equal(after.date, '2026-10-29');
  assert.match(before.title, /速記の日/);
  assert.match(after.title, /おしぼりの日/);
  assert.notEqual(before.question, after.question);
});

test('unknown dates show conversation prompts instead of an invented observance', () => {
  const tip = select(new Date('2026-10-30T03:00:00Z'));
  assert.equal(tip.kind, 'conversation');
  assert.equal(tip.sourceUrl, '');
  assert.ok(tip.question.length > 10);
  assert.doesNotMatch(tip.title, /今日は、/);
});

test('every date including leap day has one stable nonempty tip', () => {
  for (let n = 0; n < 366; n++) {
    const date = new Date(Date.UTC(2028, 0, 1 + n, 3));
    const a = select(date), b = select(new Date(date.getTime() + 3600000));
    assert.ok(a.title && a.question, date.toISOString());
    assert.equal(a.question, b.question);
    assert.ok(a.sourceUrl === '' || a.sourceUrl.startsWith('https://'));
  }
  assert.equal(select(new Date('2028-02-29T03:00:00Z')).date, '2028-02-29');
});

test('year boundary and care day retain the correct Japanese date', () => {
  assert.equal(select(new Date('2026-12-31T15:00:00Z')).date, '2027-01-01');
  assert.match(select(new Date('2026-11-11T03:00:00Z')).title, /介護の日/);
});
