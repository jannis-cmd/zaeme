const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const root = path.resolve(__dirname, '..');
async function page(config) {
  const dom = new JSDOM(fs.readFileSync(path.join(root, 'index.html'), 'utf8'), { url: 'https://example.test/hearth/', runScripts: 'outside-only' });
  const window = dom.window;
  window.fetch = async () => ({ ok: true, json: async () => config });
  window.eval(fs.readFileSync(path.join(root, 'donation.js'), 'utf8'));
  await new Promise(resolve => setImmediate(resolve));
  return window;
}
test('missing configuration never invents money or enables payment', async () => {
  const window = await page({});
  assert.equal(window.document.getElementById('donate-button').disabled, true);
  assert.equal(window.document.getElementById('donation-income').textContent, 'CHF —');
  assert.equal(window.document.getElementById('donation-comparison').hidden, true);
  assert.equal(window.document.getElementById('donation-github').hidden, true);
  window.close();
});
test('verified costs are summed and compared proportionally', async () => {
  const window = await page({ budget: { donated_chf: 100, hosting_chf: 10, ai_chf: 20, speech_chf: 30, verified_at: '2026-10-07' } });
  const doc = window.document;
  assert.equal(doc.getElementById('donation-expenses').textContent, 'CHF 60.00');
  assert.equal(doc.getElementById('donation-expenses-bar').style.width, '60%');
  assert.equal(doc.getElementById('donation-income-bar').style.width, '100%');
  assert.equal(doc.getElementById('donation-comparison').hidden, false);
  window.close();
});
test('demo amounts are explicitly labelled and never enable payments', async () => {
  const window = await page({ payment_url: 'https://pay.example.test/donate', budget: { demo: true, donated_chf: 20, hosting_chf: 1, ai_chf: 2, speech_chf: 2, verified_at: null } });
  const doc = window.document;
  assert.match(doc.getElementById('donation-budget-title').textContent, /Demo/);
  assert.equal(doc.getElementById('donation-income').textContent, 'CHF 20.00');
  assert.equal(doc.getElementById('donation-expenses').textContent, 'CHF 5.00');
  assert.match(doc.getElementById('donation-budget-note').textContent, /keine tatsächlichen Spenden/);
  assert.equal(doc.getElementById('donate-button').disabled, true);
  window.close();
});
test('unverified data and unsafe destinations are not published', async () => {
  const window = await page({ payment_url: 'javascript:alert(1)', github_url: 'https://github.com.evil.test/repo', budget: { donated_chf: 100 } });
  assert.equal(window.document.getElementById('donate-button').disabled, true);
  assert.equal(window.document.getElementById('donation-github').hidden, true);
  assert.equal(window.document.getElementById('donation-income').textContent, 'CHF —');
  window.close();
});
test('configured payment bypasses the prototype dialog and opens the provider', async () => {
  const window = await page({ payment_url: 'https://pay.example.test/donate', github_url: 'https://github.com/example/zaeme' });
  let opened;
  window.open = (...args) => { opened = args; };
  const button = window.document.getElementById('donate-button');
  button.addEventListener('click', () => assert.fail('old placeholder must not run'));
  button.click();
  assert.deepEqual(opened, ['https://pay.example.test/donate', '_blank', 'noopener,noreferrer']);
  assert.equal(window.document.getElementById('donation-github').hidden, false);
  window.close();
});
