const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const js = fs.readFileSync(path.join(root, "app.js"), "utf8");

test("overview orders people, add action, then voice on every screen size", () => {
  const dom = new JSDOM(html);
  const d = dom.window.document;
  const follows = dom.window.Node.DOCUMENT_POSITION_FOLLOWING;
  assert.ok(d.getElementById("person-grid").compareDocumentPosition(d.getElementById("new-person-button")) & follows);
  assert.ok(d.getElementById("new-person-button").compareDocumentPosition(d.querySelector(".voice-choice")) & follows);
  assert.equal(d.querySelector(".voice-choice legend").textContent, "In welcher Stimme soll Zäme sprechen");
  assert.match(d.getElementById("editor-back").textContent, /Zurück zur Übersicht/);
  assert.equal(d.querySelector(".page-head #new-person-button"), null);
});

function createPage(setup = () => {}) {
  const dom = new JSDOM(html, {
    url: "https://example.test/",
    runScripts: "dangerously",
  });
  const { window } = dom;
  Object.defineProperty(window.document, "hidden", { value: false, configurable: true });
  window.setInterval = () => 0;
  window.clearInterval = () => {};
  window.scrollTo = () => {};
  window.localStorage.setItem("zaeme.family-tour.v1", "seen");
  window.HTMLElement.prototype.scrollIntoView = () => {};
  const dialog = window.document.getElementById("app-dialog");
  dialog.showModal = () => {
    dialog.open = true;
  };
  dialog.close = (value) => {
    dialog.open = false;
    dialog.returnValue = value;
    dialog.dispatchEvent(new window.Event("close"));
  };
  setup(window);
  window.eval(js);
  const $ = (id) => window.document.getElementById(id);
  const click = (id) => $(id).click();
  const input = (id, value) => {
    $(id).value = value;
    $(id).dispatchEvent(new window.Event("input", { bubbles: true }));
  };
  const stored = () =>
    JSON.parse(window.localStorage.getItem("hearth.guest.v3"));
  return { window, $, click, input, stored, dialog };
}

test("onboarding centres fitting sections and gives oversized sections top breathing room", () => {
  const p = createPage();
  const position = (section, visible, scroll) => p.window.eval(`tourScrollDestination(${JSON.stringify(section)}, ${JSON.stringify(visible)}, ${scroll})`);
  // Available region is 100–600, independent of the card below it.
  assert.equal(position({ top: 700, bottom: 900 }, { top: 100, bottom: 600 }, 200), 650);
  assert.equal(position({ top: 700, bottom: 1300 }, { top: 100, bottom: 600 }, 200), 776);
  assert.equal(position({ top: 50, bottom: 250 }, { top: 100, bottom: 600 }, 0), 0);
});

test("first visit asks for information before showing the conversation action", () => {
  const p = createPage();
  assert.equal(p.$("home-title").textContent, "Hallo, Wer bist du?");
  assert.match(p.$("talk-button").textContent, /Für Angehörige/);
  assert.equal(
    p.window.document.body.classList.contains("needs-profile"),
    true,
  );
  assert.equal(
    p.window.document.querySelectorAll("#home-view button").length,
    1,
  );
  assert.equal(p.window.document.querySelector("#home-view .home-art"), null);
  assert.equal(p.window.document.querySelector("#home-view .kicker"), null);
  assert.equal(p.window.document.querySelector("#home-view .home-lede"), null);
  assert.equal(p.window.document.body.classList.contains("is-home"), true);
  p.click("talk-button");
  assert.equal(p.$("library-view").classList.contains("hidden"), false);
  assert.equal(p.dialog.open, false);
  assert.equal(p.stored(), null);
  p.click("new-person-button");
  assert.notEqual(p.window.document.activeElement, p.$("field-name"));
  p.window.document.querySelector('[data-view="home"]').click();
  assert.match(p.$("talk-button").textContent, /Für Angehörige/);
  p.click("talk-button");
  p.window.document.querySelector(".person-edit").click();
  p.input("field-name", "Ruth");
  p.window.document.querySelector('[data-view="home"]').click();
  assert.equal(p.$("home-title").textContent, "Hallo, Ruth.");
  assert.equal(p.$("talk-button").textContent.trim(), "Sprechen");
  p.click("talk-button");
  assert.match(p.$("home-status").textContent, /Live-Gespräche/);
  assert.equal(p.$("home-status").hidden, false);
  assert.equal(p.dialog.open, false);
  assert.equal(p.stored().daily.used, 0); // A failed preview call is not counted.
});

test("first family visit starts at people, then voice, then shows the booklet", () => {
  const p = createPage((window) => window.localStorage.removeItem("zaeme.family-tour.v1"));
  assert.equal(p.$("family-tour").hidden, true);
  p.click("talk-button");
  assert.equal(p.$("family-tour").hidden, false);
  assert.equal(p.$("library-view").classList.contains("hidden"), false);
  assert.equal(p.$("tour-title").textContent, "Personen erfassen");
  assert.match(p.$("tour-text").textContent, /Ausgewählte Menschen/);
  assert.match(p.$("tour-text").textContent, /nicht euch selbst als Angehörige/);
  p.click("tour-next");
  assert.equal(p.$("tour-title").textContent, "Stimme");
  p.click("tour-next");
  assert.equal(p.$("tour-title").textContent, "Person bearbeiten");
  assert.equal(p.stored(), null);
  p.click("tour-next");
  assert.equal(p.$("tour-title").textContent, "Wer bin ich?");
  assert.match(p.$("tour-text").textContent, /Was macht euren Menschen aus\?/);
  assert.match(p.$("tour-text").textContent, /Pfeil-Symbol rechts/);
  assert.equal(p.$("tour-text").querySelector(".inline-wordmark").textContent, "Zäme");
  assert.equal(p.$("tour-text").querySelectorAll(".inline-wordmark > span").length, 4);
  p.click("tour-next");
  assert.equal(p.$("tour-title").textContent, "Gemeinsame Erinnerungen");
  assert.equal(p.stored(), null);
  p.click("tour-next");
  assert.equal(p.$("family-tour").hidden, true);
  assert.equal(p.stored(), null);
  assert.equal(p.$("library-view").classList.contains("hidden"), false);
  assert.equal(p.$("editor-view").classList.contains("hidden"), true);
  assert.equal(p.window.document.querySelector('[data-person-id="tour-person"]'), null);
  assert.equal(p.window.document.querySelector(".editor-grid").inert, false);
  p.click("editor-back");
  assert.equal(p.$("family-tour").hidden, true);
});

test("tour booklet morphs open and closed without saving a demo profile", async () => {
  const pending = [];
  const p = createPage((window) => {
    window.localStorage.removeItem("zaeme.family-tour.v1");
    window.HTMLElement.prototype.getBoundingClientRect = function () {
      return { left: 20, top: 160, width: this.classList.contains("profile-panel") ? 600 : 250, height: 300, bottom: 460 };
    };
    window.HTMLElement.prototype.animate = function (_, options) {
      if (this.classList.contains("book-transition-paper") || this.classList.contains("book-transition-cover")) {
        return { finished: new Promise((resolve) => pending.push({ resolve, duration: options.duration })), cancel() {} };
      }
      return { cancel() {} };
    };
  });
  p.click("talk-button"); p.click("tour-next"); p.click("tour-next");
  assert.equal(p.$("tour-next").disabled, true);
  assert.equal(pending[0].duration, 360);
  pending.splice(0).forEach(animation => animation.resolve()); await new Promise(setImmediate);
  assert.equal(p.$("tour-next").disabled, false);
  assert.equal(p.$("tour-progress").textContent, "3 / 5");
  p.click("tour-next"); p.click("tour-next"); p.click("tour-next");
  assert.equal(pending[0].duration, 360);
  pending.splice(0).forEach(animation => animation.resolve()); await new Promise(setImmediate);
  assert.equal(p.$("library-view").classList.contains("hidden"), false);
  assert.equal(p.stored(), null);
  assert.equal(p.window.document.querySelector(".book-transition-stage"), null);
});

test("ordinary notebooks share the cover hinge and restore focus on close; navigation cancels safely", async () => {
  const pending = [], frames = [];
  const p = createPage(window => {
    window.localStorage.setItem("hearth.guest.v3", JSON.stringify({ version: 3, selectedIds: ["m"], people: [{ id: "m", name: "Marta", notes: [] }] }));
    window.HTMLElement.prototype.getBoundingClientRect = function () { return { left: 20, top: 100, width: 300, height: 400, bottom: 500 }; };
    window.HTMLElement.prototype.animate = function (keyframes) {
      frames.push(keyframes);
      return this.classList.contains("book-transition-paper") || this.classList.contains("book-transition-cover")
        ? { finished: new Promise(resolve => pending.push(resolve)), cancel() {} } : { cancel() {} };
    };
  });
  const mouse = element => element.dispatchEvent(new p.window.MouseEvent("click", { bubbles: true, detail: 1 }));
  const settle = async () => { pending.splice(0).forEach(resolve => resolve()); await new Promise(setImmediate); };
  p.window.document.querySelector('[data-view="library"]').click();
  mouse(p.window.document.querySelector(".person-edit"));
  assert.ok(p.window.document.querySelector(".book-transition-stage"));
  assert.equal(p.$("family-content").inert, true);
  assert.ok(frames.some(keyframes => keyframes.some(frame => frame.transform === "rotateY(-105deg)")));
  await settle();
  assert.equal(p.window.document.querySelector(".profile-panel").style.visibility, "");
  assert.equal(p.window.document.activeElement, p.$("editor-back"));
  mouse(p.$("editor-back")); await settle();
  assert.equal(p.$("library-view").classList.contains("hidden"), false);
  assert.equal(p.window.document.activeElement.className.includes("person-edit"), true);
  mouse(p.window.document.querySelector(".person-edit"));
  p.window.document.querySelector('[data-view="home"]').click();
  assert.equal(p.window.document.querySelector(".book-transition-stage"), null);
  assert.notEqual(p.$("family-content").inert, true);
  await settle();
  assert.equal(p.$("family-overlay").hidden, true);
});

test("keyboard opening and reduced motion do not hinge notebooks", () => {
  for (const reduced of [false, true]) {
    const p = createPage(window => {
      window.localStorage.setItem("hearth.guest.v3", JSON.stringify({ version: 3, selectedIds: ["m"], people: [{ id: "m", name: "Marta", notes: [] }] }));
      window.matchMedia = () => ({ matches: reduced });
      window.HTMLElement.prototype.getBoundingClientRect = () => ({ left: 20, top: 100, width: 300, height: 400, bottom: 500 });
      window.HTMLElement.prototype.animate = () => { throw new Error("should skip spatial animation"); };
    });
    p.window.document.querySelector('[data-view="library"]').click();
    p.window.document.querySelector(".person-edit").dispatchEvent(new p.window.MouseEvent("click", { bubbles: true, detail: reduced ? 1 : 0 }));
    assert.equal(p.$("editor-view").classList.contains("hidden"), false);
    assert.equal(p.window.document.querySelector(".book-transition-stage"), null);
  }
});

test("tour scrolls gently, waits for arrival to highlight, and cancels on dismissal", () => {
  let scroll = 0;
  const frames = new Map();
  let nextFrame = 0;
  const highlights = [];
  const p = createPage((window) => {
    window.localStorage.removeItem("zaeme.family-tour.v1");
    Object.defineProperty(window, "scrollY", { get: () => scroll });
    window.scrollTo = ({ top }) => { scroll = top; };
    window.requestAnimationFrame = (callback) => { frames.set(++nextFrame, callback); return nextFrame; };
    window.cancelAnimationFrame = (id) => frames.delete(id);
    window.HTMLElement.prototype.getBoundingClientRect = function () {
      const top = this.matches('.page-head, #person-grid, .person-add-row') ? 500 - scroll : 0;
      return { top, bottom: top + 100, width: 200, height: 100 };
    };
    window.HTMLElement.prototype.animate = function () { highlights.push(this); return { cancel() {} }; };
  });
  const tick = (time) => {
    const entries = [...frames.values()]; frames.clear(); entries.forEach((callback) => callback(time));
  };
  p.click("talk-button");
  assert.equal(scroll, 0);
  assert.equal(p.$("tour-next").disabled, true);
  assert.equal(highlights.length, 0);
  tick(0); tick(500);
  assert.ok(scroll > 0 && scroll < 376);
  assert.equal(highlights.length, 0);
  tick(1100);
  assert.equal(scroll, 376);
  assert.equal(p.$("tour-next").disabled, false);
  assert.equal(highlights.length, 2);
  p.click("tour-next");
  assert.equal(frames.size, 1);
  p.click("tour-skip");
  assert.equal(frames.size, 0);
  assert.equal(p.$("tour-next").disabled, false);
});

test("tour skip and Escape are remembered, saved profiles never trigger it", () => {
  const p = createPage((window) => window.localStorage.removeItem("zaeme.family-tour.v1"));
  p.click("talk-button");
  p.window.document.dispatchEvent(new p.window.KeyboardEvent("keydown", { key: "Escape" }));
  assert.equal(p.$("family-tour").hidden, true);
  assert.equal(p.stored(), null);
  p.click("talk-button");
  assert.equal(p.$("family-tour").hidden, true);
  const returning = createPage((window) => {
    window.localStorage.removeItem("zaeme.family-tour.v1");
    window.localStorage.setItem("hearth.guest.v3", JSON.stringify({ version: 3, people: [{ id: "h", name: "Hilde", notes: [] }] }));
  });
  returning.window.document.querySelector('[data-view="library"]').click();
  assert.equal(returning.$("family-tour").hidden, true);
});

test("tour aligns whole sections and briefly emphasizes titles then refresh", () => {
  const animations = [];
  const scrolls = [];
  const p = createPage((window) => {
    window.localStorage.removeItem("zaeme.family-tour.v1");
    window.scrollTo = (options) => scrolls.push(options);
    window.HTMLElement.prototype.animate = function (frames, options) {
      animations.push({ element: this, options });
      return { cancel() {} };
    };
  });
  p.click("talk-button");
  assert.equal(p.window.document.querySelector(".tour-target").classList.contains("page-head"), true);
  assert.equal(animations.length, 2);
  assert.equal(animations[0].element.id, "library-title");
  assert.equal(animations[1].options.delay, 660);
  p.click("tour-next");
  assert.equal(p.window.document.querySelector(".tour-target").classList.contains("voice-section"), true);
  assert.equal(animations.at(-3).element.id, "voice-title");
  assert.equal(animations.at(-1).element.tagName, "LABEL");
  p.click("tour-next");
  animations.length = 0;
  assert.equal(p.window.document.querySelector(".tour-target").classList.contains("editor-heading"), true);
  assert.equal(scrolls.at(-1).behavior, "instant");
  assert.equal(animations.length, 0);
  p.click("tour-next");
  assert.equal(p.window.document.querySelector(".tour-target").classList.contains("compiled-title"), true);
  assert.equal(animations[0].element.tagName, "H3");
  assert.equal(animations[1].element.id, "compile-button");
  assert.equal(animations[0].options.delay, 240);
  assert.equal(animations[1].options.delay, 660);
  assert.equal(animations[0].options.duration, 1000);
  p.click("tour-next");
  assert.equal(p.window.document.querySelector(".tour-target").classList.contains("notes-panel"), true);
  assert.equal(animations[2].element.id, "notes-heading");
  assert.equal(animations[3].element.id, "note-form");
});

test("tour demonstrates a blank person without persisting selection or a profile", () => {
  const timers = [];
  const p = createPage((window) => {
    window.localStorage.removeItem("zaeme.family-tour.v1");
    window.setTimeout = (callback, delay) => { const timer = { callback, delay }; timers.push(timer); return timer; };
    window.clearTimeout = (timer) => { timer.cancelled = true; };
  });
  p.click("talk-button");
  const demo = p.window.document.querySelector('[data-person-id="tour-person"]');
  assert.equal(demo.querySelector("h3").textContent, "Neue Person");
  assert.equal(p.stored(), null);
  const showing = p.window.document.querySelector('[data-person-id="tour-person"]');
  assert.deepEqual(timers.map((timer) => timer.delay), [1300, 2800]);
  timers[0].callback();
  assert.equal(showing.classList.contains("is-selected"), true);
  timers[1].callback();
  assert.equal(showing.classList.contains("is-selected"), false);
  showing.querySelector(".person-select").click();
  assert.equal(showing.classList.contains("is-selected"), true);
  assert.equal(p.stored(), null);
  p.click("tour-next");
  assert.equal(p.$("tour-title").textContent, "Stimme");
  p.click("tour-next");
  assert.equal(p.$("editor-title").textContent, "Neue Person");
  assert.equal(p.$("field-name").value, "");
  assert.equal(timers.every((timer) => timer.cancelled), true);
  p.click("tour-skip");
  assert.equal(p.window.document.querySelector('[data-person-id="tour-person"]'), null);
});

test("tour repeats highlights and demo every five seconds and cleans up on step change", () => {
  const loops = [];
  const pops = [];
  const timers = [];
  const p = createPage((window) => {
    window.localStorage.removeItem("zaeme.family-tour.v1");
    window.setInterval = (callback, delay) => { const loop = { callback, delay }; loops.push(loop); return loop; };
    window.clearInterval = (loop) => { if (loop) loop.cancelled = true; };
    window.setTimeout = (callback, delay) => { const timer = { callback, delay }; timers.push(timer); return timer; };
    window.clearTimeout = (timer) => { timer.cancelled = true; };
    window.HTMLElement.prototype.animate = function () { pops.push(this); return { cancel() {} }; };
  });
  p.click("talk-button");
  assert.equal(loops[0].delay, 5000);
  assert.equal(pops.length, 2);
  loops[0].callback();
  assert.equal(pops.length, 4);
  Object.defineProperty(p.window.document, "hidden", { value: true, configurable: true });
  loops[0].callback();
  assert.equal(pops.length, 4);
  Object.defineProperty(p.window.document, "hidden", { value: false, configurable: true });
  timers.filter(timer => !timer.cancelled)[0].callback();
  assert.equal(p.window.document.querySelector('.person-card').classList.contains('is-selected'), true);
  timers.filter(timer => !timer.cancelled)[1].callback();
  assert.equal(p.window.document.querySelector('.person-card').classList.contains('is-selected'), false);
  assert.equal(timers.length, 4);
  p.click("tour-next");
  assert.equal(loops[0].cancelled, true);
  assert.equal(loops[1].delay, 5000);
  const before = pops.length;
  loops[1].callback();
  assert.equal(pops.length, before + 3);
  p.click("tour-skip");
  assert.equal(loops[1].cancelled, true);
  assert.equal(timers.every((timer) => timer.cancelled), true);
});

test("tour respects reduced motion", () => {
  const p = createPage((window) => {
    window.localStorage.removeItem("zaeme.family-tour.v1");
    window.matchMedia = () => ({ matches: true });
    window.HTMLElement.prototype.animate = () => { throw new Error("Must not animate"); };
  });
  p.click("talk-button");
  p.click("tour-next");
  p.click("tour-next");
  assert.equal(p.$("tour-progress").textContent, "3 / 5");
});

test("present people toggle independently; editing and reload preserve selection", () => {
  const record = { version: 3, selectedIds: ["h", "r"], people: [
    { id: "h", name: "Hilde", notes: [] }, { id: "r", name: "Ruth", notes: [] }
  ] };
  const p = createPage((window) => window.localStorage.setItem("hearth.guest.v3", JSON.stringify(record)));
  assert.equal(p.$("home-title").textContent, "Hallo, Hilde und Ruth.");
  p.window.document.querySelector('[data-view="library"]').click();
  assert.equal(p.window.document.querySelectorAll('.person-select[aria-pressed="true"]').length, 2);
  assert.equal(p.window.document.querySelectorAll('.person-selection .icon-check').length, 2);
  p.window.document.querySelector(".person-select").click();
  assert.deepEqual(p.stored().selectedIds, ["r"]);
  p.window.document.querySelectorAll(".person-edit")[1].click();
  p.input("field-name", "Hilde Neu");
  assert.deepEqual(p.stored().selectedIds, ["r"]);
  p.click("editor-back");
  p.window.document.querySelector('.person-select[aria-pressed="true"]').click();
  assert.deepEqual(p.stored().selectedIds, []);
  const reload = createPage((window) => window.localStorage.setItem("hearth.guest.v3", JSON.stringify(p.stored())));
  assert.match(reload.$("talk-button").textContent, /Für Angehörige/);
});

test("navigation marks the active section, including the person editor", () => {
  const p = createPage();
  const library = p.window.document.querySelector('.nav-link[data-view="library"]');
  const donate = p.window.document.querySelector('.nav-link[data-view="donate"]');
  assert.equal(library.hasAttribute("aria-current"), false);
  assert.equal(donate.hasAttribute("aria-current"), false);

  library.click();
  assert.equal(library.getAttribute("aria-current"), "page");
  p.click("new-person-button");
  assert.equal(library.getAttribute("aria-current"), "page");

  donate.click();
  assert.equal(library.hasAttribute("aria-current"), false);
  assert.equal(donate.getAttribute("aria-current"), "page");
  p.window.document.querySelector('.nav-speak[data-view="home"]').click();
  assert.equal(donate.hasAttribute("aria-current"), false);
  assert.equal(p.$("home-view").classList.contains("hidden"), false);
});

test("family overlay keeps sections together and closes back to its opener", () => {
  const p = createPage();
  p.$("talk-button").focus();
  p.click("talk-button");
  assert.equal(p.$("family-overlay").hidden, false);
  assert.equal(p.$("home-view").inert, true);
  assert.equal(p.$("family-panel").contains(p.$("library-view")), true);
  assert.equal(p.$("family-content").contains(p.$("library-view")), true);
  assert.equal(p.$("family-content").contains(p.window.document.querySelector(".site-header")), false);
  assert.equal(p.$("family-tour").parentElement, p.$("family-panel"));
  assert.equal(p.$("family-content").contains(p.$("family-tour")), false);
  p.window.document.querySelector('.nav-link[data-view="donate"]').click();
  assert.equal(p.$("family-overlay").hidden, false);
  p.window.document.dispatchEvent(new p.window.KeyboardEvent("keydown", { key: "Escape" }));
  assert.equal(p.$("family-overlay").hidden, true);
  assert.equal(p.$("home-view").inert, false);
  assert.equal(p.window.document.activeElement, p.$("talk-button"));
});

test("section changes reset only the inner overlay scroll area", () => {
  const p = createPage();
  p.click("talk-button");
  p.click("tour-skip");
  const calls = [];
  p.$("family-content").scrollTo = options => calls.push(options);
  p.$("family-overlay").scrollTo = () => assert.fail("the window frame must not scroll");
  p.window.document.querySelector('.nav-link[data-view="donate"]').click();
  assert.deepEqual(calls.map(call => call.top), [0]);
});

test("family voice choice is persisted without changing the profile", () => {
  const p = createPage();
  p.window.document.querySelector('[data-view="library"]').click();
  assert.equal(p.window.document.querySelector('input[value="female"]').checked, true);
  p.window.document.querySelector('input[value="male"]').click();
  assert.equal(p.stored().voiceGender, "male");
  assert.deepEqual(p.stored().people, []);
});


test("live turns use native VAD finals, stream silence and resume after replies", async () => {
  const calls = [];
  let stopped = 0;
  let socket;
  let worklet;
  let playback;
  let silenceCheck;
  let clock = 0;
  const p = createPage((window) => {
    window.performance.now = () => clock;
    window.setInterval = (callback) => { silenceCheck = callback; return 1; };
    window.clearInterval = () => { silenceCheck = null; };
    window.navigator.mediaDevices = {
      getUserMedia: async () => {
        const track = { enabled: true, stop: () => stopped++ };
        return { getTracks: () => [track], getAudioTracks: () => [track] };
      },
    };
    window.AudioContext = class {
      constructor() { this.sampleRate = 48000; this.audioWorklet = { addModule: async () => {} }; this.destination = {}; }
      createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
      createBufferSource() { playback = { connect() {}, addEventListener(name, fn) { this[name] = fn; }, start() {}, stop() {} }; return playback; }
      decodeAudioData() { return Promise.resolve({}); }
      resume() { return Promise.resolve(); }
      close() { return Promise.resolve(); }
    };
    window.AudioWorkletNode = class { constructor() { this.port = {}; worklet = this; } connect() {} disconnect() {} };
    window.WebSocket = class {
      static OPEN = 1;
      constructor(url) { this.url = url; this.readyState = 1; this.listeners = {}; this.sent = []; socket = this; queueMicrotask(() => this.emit("open")); }
      addEventListener(name, listener) { (this.listeners[name] ||= []).push(listener); }
      emit(name, data = {}) { for (const listener of this.listeners[name] || []) listener(data); }
      close() { this.readyState = 3; this.emit("close"); }
      send(message) { this.sent.push(JSON.parse(message)); }
    };
    window.fetch = async (url, options) => {
      calls.push({ url, options });
      if (url === "api/status") return { ok: true, json: async () => ({ realtime_ready: true, voice_ready: true, model_ready: true }) };
      if (url === "api/scribe-token") return { ok: true, json: async () => ({ token: "test-once" }) };
      if (url === "api/chat") return { ok: true, json: async () => ({ response: "Guten Tag." }) };
      if (url === "api/speak") return { ok: true, blob: async () => ({ arrayBuffer: async () => new ArrayBuffer(4) }) };
      throw new Error(`Unexpected ${url}`);
    };
  });
  p.click("new-person-button");
  p.input("field-name", "Ruth");
  p.click("editor-back");
  p.click("library-home");
  p.click("talk-button");
  await new Promise(setImmediate);
  const params = new URL(socket.url).searchParams;
  assert.equal(params.get("commit_strategy"), "vad");
  assert.equal(params.get("min_silence_duration_ms"), "100");
  assert.equal(params.get("vad_silence_threshold_secs"), "2.0");
  assert.match(p.$("talk-button").textContent, /Gespräch beenden/);
  socket.emit("message", { data: JSON.stringify({ message_type: "partial_transcript", text: "Grüe" }) });
  assert.equal(p.$("live-transcript").textContent, "Grüe");
  socket.emit("message", { data: JSON.stringify({ message_type: "committed_transcript", text: "Grüezi" }) });
  await new Promise(setImmediate);
  assert.equal(p.$("live-transcript").textContent, "Grüezi");
  assert.deepEqual(calls.map((call) => call.url), ["api/status", "api/scribe-token", "api/chat", "api/speak"]);
  assert.equal(JSON.parse(calls.at(-1).options.body).voice, "female");
  assert.equal(p.$("home-status").textContent, "Guten Tag.");
  assert.equal(p.stored().daily.used, 1);
  playback.ended();
  assert.equal(p.$("home-status").textContent, "Ich höre zu …");
  socket.emit("message", { data: JSON.stringify({ message_type: "partial_transcript", text: "Was muss ich heute für Tabletten nehmen?" }) });
  for (clock = 250; clock <= 7250; clock += 250) {
    worklet.port.onmessage({ data: new ArrayBuffer(4) });
    silenceCheck();
  }
  await new Promise(setImmediate);
  assert.equal(socket.sent.filter((chunk) => chunk.commit).length, 0);
  assert.equal(calls.filter((call) => call.url === "api/chat").length, 1);
  socket.emit("message", { data: JSON.stringify({ message_type: "committed_transcript", text: "Was muss ich heute für Tabletten nehmen?" }) });
  await new Promise(setImmediate);
  assert.equal(calls.filter((call) => call.url === "api/chat").length, 2);
  assert.equal(p.stored().daily.used, 2);
  // Duplicate finals while the reply is processing must not create a second turn.
  socket.emit("message", { data: JSON.stringify({ message_type: "committed_transcript", text: "Was muss ich heute für Tabletten nehmen?" }) });
  await new Promise(setImmediate);
  assert.equal(calls.filter((call) => call.url === "api/chat").length, 2);
  playback.ended();
  clock += 9000;
  silenceCheck();
  assert.match(p.$("home-status").textContent, /Mikrofon wurde unterbrochen/);
  assert.equal(stopped, 1);
  assert.equal(silenceCheck, null);
  p.click("talk-button");
  await new Promise(setImmediate);
  socket.emit("message", { data: JSON.stringify({ message_type: "partial_transcript", text: "Ein letzter Satz." }) });
  assert.equal(p.$("live-transcript").hidden, false);
  p.click("talk-button");
  assert.equal(p.$("live-transcript").textContent, "");
  assert.equal(p.$("live-transcript").hidden, true);
  assert.equal(p.$("home-status").textContent, "Gespräch beendet.");
});

test("selected person stays first and the limit message replaces the add button", () => {
  const p = createPage();
  p.window.document.querySelector('[data-view="library"]').click();
  p.click("new-person-button");
  p.input("field-name", "Ruth");
  p.click("editor-back");
  assert.equal(p.$("library-home-label").textContent, "Zum Gespräch");
  p.click("library-home");
  assert.equal(p.$("home-view").classList.contains("hidden"), false);
  assert.equal(p.$("home-title").textContent, "Hallo, Ruth.");
  p.window.document.querySelector('[data-view="library"]').click();
  assert.equal(
    p.window.document.querySelector(".person-card h3").textContent,
    "Ruth",
  );
  assert.equal(
    p.window.document
      .querySelector(".person-card")
      .classList.contains("is-selected"),
    true,
  );
  p.click("new-person-button");
  p.input("field-name", "Hans");
  p.click("editor-back");
  p.window.document.querySelectorAll(".person-select")[1].click();
  assert.equal(
    p.window.document.querySelector(".person-card h3").textContent,
    "Ruth",
  );
  assert.equal(
    p.stored().people.find((x) => x.id === p.stored().selectedId).name,
    "Ruth",
  );
  p.window.document.querySelector(".person-edit").click();
  assert.equal(p.$("editor-title").textContent, "Ruth");
  p.click("editor-back");
  p.click("new-person-button");
  p.input("field-name", "Marta");
  assert.equal(p.stored().people.length, 3);
  p.click("editor-back");
  assert.equal(p.$("new-person-button").hidden, true);
  assert.equal(p.$("person-limit-message").hidden, false);
  assert.match(p.$("person-limit-message").textContent, /drei Personen/);
  assert.deepEqual(
    p.stored().people.map((x) => x.name),
    ["Ruth", "Hans", "Marta"],
  );
});

test("saved named profile is automatically active and first on reload", () => {
  const p = createPage((window) => {
    window.localStorage.setItem(
      "hearth.guest.v3",
      JSON.stringify({
        version: 3,
        selectedId: "blank",
        people: [
          { id: "blank", name: "", notes: [] },
          { id: "ruth", name: "Ruth", notes: [] },
          { id: "hans", name: "Hans", notes: [] },
        ],
      }),
    );
  });
  assert.equal(p.$("home-title").textContent, "Hallo, Ruth.");
  p.window.document.querySelector('[data-view="library"]').click();
  assert.equal(
    p.window.document.querySelector(".person-card h3").textContent,
    "Ruth",
  );
  assert.equal(p.$("library-home-label").textContent, "Zum Gespräch");
});

test("edits notes, removes oldest at cap, and invalidates compiled persona", () => {
  const p = createPage();
  p.click("new-person-button");
  const id = p.stored().selectedId;
  for (let i = 0; i < 13; i++) {
    p.input("note-text", `Erinnerung ${i}`);
    p.$("note-form").dispatchEvent(
      new p.window.Event("submit", { bubbles: true, cancelable: true }),
    );
  }
  let person = p.stored().people.find((x) => x.id === id);
  assert.equal(person.notes.length, 12);
  assert.equal(
    person.notes.some((x) => x.text === "Erinnerung 0"),
    false,
  );
  assert.match(p.$("note-form-hint").textContent, /älteste/);
  assert.equal(p.window.document.querySelectorAll(".note-card").length, 12);
  assert.equal(
    p.window.document.querySelector(".note-card p").textContent,
    "Erinnerung 12",
  );
  assert.equal(
    p.window.document.querySelector(".note-edit").getAttribute("aria-label"),
    "Erinnerung bearbeiten",
  );
  p.window.document.querySelector(".note-card-actions button").click();
  p.input("note-text", "Geänderte Erinnerung");
  p.$("note-form").dispatchEvent(
    new p.window.Event("submit", { bubbles: true, cancelable: true }),
  );
  person = p.stored().people.find((x) => x.id === id);
  assert.equal(person.notes.at(-1).text, "Geänderte Erinnerung");
  assert.equal(person.compiled, null);
  assert.equal(person.personaNeedsRefresh, true);
  assert.equal(p.$("compile-button").classList.contains("needs-refresh"), true);
});

test("new memory animates into the top of the list", () => {
  const animations = [];
  const p = createPage((window) => {
    window.HTMLElement.prototype.animate = function (frames, options) {
      animations.push({ element: this, frames, options });
      return { cancel() {} };
    };
  });
  p.click("new-person-button");
  p.input("note-text", "Ein Besuch im Garten");
  p.$("note-form").dispatchEvent(
    new p.window.Event("submit", { bubbles: true, cancelable: true }),
  );
  assert.equal(
    p.window.document.querySelector(".note-card p").textContent,
    "Ein Besuch im Garten",
  );
  assert.equal(animations.length, 1);
  assert.equal(animations[0].options.duration, 280);
  assert.match(animations[0].frames[0].transform, /translateY\(-32px\)/);
});

test("memory bubbles expand independently of editing and collapse with Escape", () => {
  const p = createPage();
  p.click("new-person-button");
  p.input("note-text", "Eine lange Erinnerung an einen gemeinsamen Tag im Garten. ".repeat(6));
  p.click("save-note-button");
  const card = p.window.document.querySelector(".note-card");
  const toggle = card.querySelector(".note-toggle");
  const snapshot = JSON.stringify(p.stored().people[0].notes);
  toggle.click();
  assert.equal(toggle.getAttribute("aria-expanded"), "true");
  card.querySelector(".note-edit").click();
  assert.equal(toggle.getAttribute("aria-expanded"), "true");
  assert.match(p.$("note-text").value, /gemeinsamen Tag/);
  card.dispatchEvent(new p.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  assert.equal(toggle.getAttribute("aria-expanded"), "false");
  assert.equal(card.classList.contains("is-expanded"), false);
  assert.equal(JSON.stringify(p.stored().people[0].notes), snapshot);
});

test("voice availability, sync confirmation, login, and donation states", () => {
  const p = createPage();
  p.click("login-button");
  assert.match(p.$("dialog-title").textContent, /Anmeldung folgt/);
  p.dialog.close("close");
  p.click("new-person-button");
  p.click("record-note-button");
  assert.match(p.$("note-form-hint").textContent, /keine Mikrofonaufnahme/);
  p.click("compile-button");
  assert.match(
    p.$("dialog-message").textContent,
    /gemeinsamen Erinnerungen neu zusammengefasst/,
  );
  p.dialog.close("confirm");
  assert.match(p.$("dialog-title").textContent, /Noch keine Erinnerungen/);
  p.dialog.close("close");
  p.window.document.querySelector('[data-view="donate"]').click();
  assert.equal(p.$("donate-button").disabled, true);
  assert.match(p.$("donation-payment-note").textContent, /wird noch eingerichtet/);
});

test("persona refresh uses the model gateway and saves verified response", async () => {
  let request;
  const p = createPage((window) => {
    window.fetch = async (url, options) => {
      request = { url, options };
      return {
        ok: true,
        json: async () => ({ summary: "Ruth mag ihren Garten.", passages: [{ title: "Was ich gerne mache", text: "Ich mag meinen Garten." }], fields: { name: "Ruth", age: "81" } }),
      };
    };
  });
  p.click("new-person-button");
  p.input("note-text", "Ruth mag ihren Garten.");
  p.click("save-note-button");
  p.click("compile-button");
  p.dialog.close("confirm");
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(request.url, "api/persona");
  assert.deepEqual(JSON.parse(request.options.body).profile.notes, ["Ruth mag ihren Garten."]);
  assert.equal(p.stored().people[0].compiled, "Ruth mag ihren Garten.");
  assert.equal(p.stored().people[0].personaNeedsRefresh, false);
  assert.equal(p.$("compile-button").classList.contains("needs-refresh"), false);
  assert.equal(p.stored().people[0].name, "Ruth");
  assert.equal(p.$("compiled-content").querySelector("h4").textContent, "Was ich gerne mache");
  assert.equal(p.$("compiled-content").querySelector("p").textContent, "Ich mag meinen Garten.");
  p.input("note-text", "Eine weitere Erinnerung.");
  p.click("save-note-button");
  assert.equal(p.stored().people[0].passages.length, 0);
  assert.equal(p.$("compile-button").disabled, false);
});

test("recording transcribes into the composer before a separate save", async () => {
  let uploads = 0;
  const p = createPage((window) => {
    window.navigator.mediaDevices = {
      getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }),
    };
    window.requestAnimationFrame = () => 1;
    window.cancelAnimationFrame = () => {};
    window.MediaRecorder = class extends window.EventTarget {
      state = "inactive";
      mimeType = "audio/webm";
      constructor(stream) {
        super();
        this.stream = stream;
      }
      start() {
        this.state = "recording";
      }
      stop() {
        this.state = "inactive";
        const event = new window.Event("dataavailable");
        event.data = new window.Blob(["voice"], { type: this.mimeType });
        this.dispatchEvent(event);
        this.dispatchEvent(new window.Event("stop"));
      }
    };
    window.fetch = async (url) => {
      assert.equal(url, "api/transcribe");
      uploads++;
      return { ok: true, json: async () => ({ text: "Sie mag Rosen." }) };
    };
  });
  p.click("new-person-button");
  p.click("record-note-button");
  await new Promise(setImmediate);
  assert.equal(p.$("recording-panel").hidden, false);
  assert.equal(p.$("recording-waveform").children.length, 29);
  p.click("discard-recording");
  assert.equal(p.$("recording-panel").hidden, true);
  assert.equal(uploads, 0);
  p.click("record-note-button");
  await new Promise(setImmediate);
  p.click("confirm-recording");
  await new Promise(setImmediate);
  assert.equal(uploads, 1);
  assert.equal(p.$("note-text").value, "Sie mag Rosen.");
  assert.equal(p.stored().people[0].notes.length, 0);
  p.$("note-form").dispatchEvent(
    new p.window.Event("submit", { bubbles: true, cancelable: true }),
  );
  assert.equal(p.stored().people[0].notes[0].text, "Sie mag Rosen.");
});

test("deletes a note and its owner only after explicit confirmation", () => {
  const p = createPage();
  p.click("new-person-button");
  p.input("field-name", "Ruth");
  p.input("note-text", "Mag Spaziergänge");
  p.$("note-form").dispatchEvent(
    new p.window.Event("submit", { bubbles: true, cancelable: true }),
  );
  assert.equal(
    p.stored().people.find((x) => x.name === "Ruth").notes.length,
    1,
  );
  p.window.document.querySelector(".delete-note").click();
  assert.equal(
    p.stored().people.find((x) => x.name === "Ruth").notes.length,
    1,
  );
  p.dialog.close("confirm");
  assert.equal(
    p.stored().people.find((x) => x.name === "Ruth").notes.length,
    0,
  );
  p.click("delete-person-button");
  p.dialog.close("cancel");
  assert.equal(p.stored().people.length, 1);
  p.click("delete-person-button");
  p.dialog.close("confirm");
  assert.equal(p.stored().people.length, 0);
  assert.equal(p.stored().selectedId, null);
});

test("migrates older guest data without keeping the fictional sample", () => {
  const p = createPage((window) => {
    window.localStorage.setItem(
      "hearth.guest.v2",
      JSON.stringify({
        version: 2,
        selectedId: "sample-marta",
        daily: { date: "", used: 0 },
        people: [
          { id: "sample-marta", name: "Marta", sample: true, notes: [] },
          { id: "real-ruth", name: "Ruth", sample: false, notes: [] },
        ],
      }),
    );
  });
  assert.equal(p.$("home-title").textContent, "Hallo, Ruth.");
  p.window.document.querySelector('[data-view="library"]').click();
  assert.equal(p.window.document.querySelectorAll(".person-card").length, 1);
  assert.equal(
    p.window.document.querySelector(".person-card h3").textContent,
    "Ruth",
  );
});
