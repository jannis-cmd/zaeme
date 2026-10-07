/* Zäme guest preview. Keep the existing storage key to preserve saved profiles. */
const STORAGE_KEY = "hearth.guest.v3";
const LEGACY_STORAGE_KEY = "hearth.guest.v2";
const TOUR_KEY = "zaeme.family-tour.v1";
let tourStep = -1;
let tourAnimations = [];
let tourTimers = [];
let tourLoop = null;
let tourMorph = null;
let cancelTourScroll = null;
let overlayOpener = null;
let bookTransition = null;
let bookNavigating = false;
let libraryScroll = 0;
function scrollSurface() {
  const overlay = document.getElementById("family-overlay");
  const content = document.getElementById("family-content");
  return overlay && !overlay.hidden && typeof content?.scrollTo === "function" ? content : window;
}
function scrollPosition() { const surface = scrollSurface(); return surface === window ? window.scrollY : surface.scrollTop; }
function tourScrollInset() {
  const surface = scrollSurface();
  return surface === window ? Math.max(48, document.querySelector(".site-header").getBoundingClientRect().height + 24) : surface.getBoundingClientRect().top + 24;
}
let tourPersonSelected = false;
const tourPerson = { id: "tour-person", name: "", notes: [], language: "Schweizerdeutsch", address: "Sie" };
if ("scrollRestoration" in history) history.scrollRestoration = "manual";
const LIMITS = Object.freeze({ people: 3, notes: 12, conversationsPerDay: 5 });
const $ = (id) => document.getElementById(id);
function brandMentions(element) {
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
  const matches = [];
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.textContent.includes("Zäme") && !node.parentElement.closest(".wordmark, textarea, input, script, style")) matches.push(node);
  }
  for (const node of matches) {
    const fragment = document.createDocumentFragment();
    for (const part of node.textContent.split(/(Zäme)/)) {
      if (part !== "Zäme") { fragment.append(document.createTextNode(part)); continue; }
      const word = document.createElement("span");
      word.className = "wordmark inline-wordmark";
      for (const letter of part) {
        const span = document.createElement("span");
        span.textContent = letter;
        word.append(span);
      }
      fragment.append(word);
    }
    node.replaceWith(fragment);
  }
}
const makeId = () =>
  globalThis.crypto?.randomUUID?.() ||
  `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const initialState = () => ({
  version: 3,
  selectedId: null,
  selectedIds: [],
  daily: { date: "", used: 0 },
  voiceGender: "female",
  people: [],
});
function loadState() {
  try {
    const saved = JSON.parse(
      localStorage.getItem(STORAGE_KEY) ||
        localStorage.getItem(LEGACY_STORAGE_KEY),
    );
    if (
      (saved?.version === 2 || saved?.version === 3) &&
      Array.isArray(saved.people)
    ) {
      saved.people = saved.people
        .filter(
          (person) =>
            !(
              saved.version === 2 &&
              person.id === "sample-marta" &&
              person.sample
            ),
        )
        .slice(0, LIMITS.people)
        .map((person) => ({
          ...person,
          notes: Array.isArray(person.notes)
            ? person.notes.slice(-LIMITS.notes)
            : [],
        }));
      const remembered = saved.people.find(
        (person) => person.id === saved.selectedId && person.name?.trim(),
      );
      saved.selectedId =
        remembered?.id ||
        saved.people.find((person) => person.name?.trim())?.id ||
        saved.people[0]?.id ||
        null;
      saved.selectedIds = Array.isArray(saved.selectedIds)
        ? [...new Set(saved.selectedIds)].filter((id) => saved.people.some((person) => person.id === id))
        : saved.selectedId ? [saved.selectedId] : [];
      saved.selectedId = saved.selectedIds[0] || null;
      saved.version = 3;
      saved.voiceGender = saved.voiceGender === "male" ? "male" : "female";
      return saved;
    }
  } catch {
    /* A broken local record must not stop the page. */
  }
  return initialState();
}
let state = loadState();
let editingId = null;
let noteEditingId = null;
let lastAddedNoteId = null;
let recordingState = null;
let recordingRequest = 0;
let conversationState = null;
let conversationRequest = 0;
let conversationMessages = [];
let conversationPersonId = null;
let replyAudio = null;
let conversationConnecting = false;
let conversationDiagnostics = [];
function traceConversation(event, details = {}) {
  conversationDiagnostics.push({ at: Date.now(), event, ...details });
  if (conversationDiagnostics.length > 100) conversationDiagnostics.shift();
}
function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    return true;
  } catch {
    showDialog(
      "Speichern nicht möglich",
      "Der Browser konnte die Daten nicht lokal speichern. Bitte prüfen Sie, ob privates Surfen oder voller Gerätespeicher das Speichern verhindert.",
    );
    return false;
  }
}
function currentPerson() {
  return state.people.find((person) => person.id === editingId) || (tourStep >= 0 ? tourPerson : null);
}
function selectedPeople() {
  return state.people.filter((person) => state.selectedIds.includes(person.id) && person.name?.trim());
}
function setSelection(ids) {
  state.selectedIds = ids;
  state.selectedId = ids[0] || null;
  conversationMessages = [];
  conversationPersonId = null;
}
function showView(name, touring = false) {
  if (!bookNavigating) bookTransition?.();
  const overlay = $("family-overlay");
  const opening = name !== "home" && overlay.hidden;
  if (opening) overlayOpener = document.activeElement;
  if (tourStep >= 0 && !touring) finishTour(false, false);
  if (name !== "home") stopConversation();
  if (name !== "home") setLiveTranscript("");
  if (name !== "editor") {
    recordingRequest++;
    if (recordingState) discardRecording();
  }
  document.body.classList.toggle("is-home", name === "home");
  overlay.hidden = name === "home";
  document.querySelector(".home-header").inert = name !== "home";
  $("home-view").inert = name !== "home";
  $("home-view").setAttribute("aria-hidden", String(name !== "home"));
  for (const view of ["home", "library", "editor", "donate"])
    $(`${view}-view`).classList.toggle("hidden", view !== "home" && view !== name);
  for (const link of document.querySelectorAll(".nav-link")) {
    const active =
      link.dataset.view === (name === "editor" ? "library" : name);
    link.classList.toggle("is-active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  if (name === "library") renderLibrary();
  if (name === "home") {
    setHomeStatus("");
    renderHome();
  }
  if (name === "editor") renderEditor();
  if (!touring) scrollSurface().scrollTo({ top: 0, behavior: "instant" });
  if (opening) document.querySelector('.nav-link[data-view="library"]').focus({ preventScroll: true });
  if (name === "home" && overlayOpener) { overlayOpener.focus({ preventScroll: true }); overlayOpener = null; }
  if (tourStep < 0 && name === "library" && !state.people.some((person) => person.name?.trim())) {
    try { if (!localStorage.getItem(TOUR_KEY)) { tourStep = 0; editingId = null; showTourStep(); } } catch { /* Optional help. */ }
  }
}
function showTourStep(instant = false) {
  cancelTourScroll?.();
  clearInterval(tourLoop);
  tourLoop = null;
  tourTimers.forEach(clearTimeout);
  tourTimers = [];
  tourPersonSelected = false;
  tourAnimations.forEach((animation) => animation.cancel());
  tourAnimations = [];
  document.querySelectorAll(".tour-target").forEach((element) => element.classList.remove("tour-target"));
  const steps = [
    ["Personen erfassen", "Hier erfasst ihr euren Menschen mit Demenz – nicht euch selbst als Angehörige. Mit dem Stift bearbeitet ihr Profile. Tippt an, wer beim Gespräch dabei ist. Ausgewählte Menschen sind grün markiert.", "#library-view .page-head"],
    ["Stimme", "Hier kannst du wählen, ob Zäme mit einer männlichen oder weiblichen Stimme sprechen soll.", ".voice-section"],
    ["Person bearbeiten", "Zäme begleitet Menschen mit Demenz im Gespräch. Als Angehörige füllt ihr dieses Profil wie ein Freundschaftsbuch: mit Namen, Vorlieben und gemeinsamen Erinnerungen.", ".editor-heading"],
    ["Wer bin ich?", "Was macht euren Menschen aus? Hier fasst Zäme eure Erinnerungen zusammen, die ihr unten erfasst habt. Die Zusammenfassung muss jeweils mit dem Pfeil-Symbol rechts aktualisiert werden, wenn ihr neue Erinnerungen hinzufügt.", ".compiled-title"],
    ["Gemeinsame Erinnerungen", "Ein Ausflug, ein Lieblingslied oder ein vertrautes Ritual: Schreibt auf, was euch verbindet, oder erzählt es ins Mikrofon. Gespeicherte Erinnerungen könnt ihr antippen und mit dem Stift bearbeiten. Danach geht’s zurück zur Personenübersicht. Mit dem Kreuz oben rechts schliesst ihr das Fenster und kommt zurück zum Gespräch.", ".notes-panel"],
  ];
  showView(tourStep < 2 ? "library" : "editor", true);
  $("editor-view").querySelector(".editor-grid").inert = true;
  $("editor-back").disabled = true;
  $("delete-person-button").hidden = true;
  const [title, text, selector] = steps[tourStep];
  $("tour-title").textContent = title;
  brandMentions($("tour-title"));
  $("tour-text").textContent = text;
  brandMentions($("tour-text"));
  $("tour-progress").textContent = `${tourStep + 1} / 5`;
  $("tour-next").setAttribute("aria-label", tourStep === 4 ? "Zur Personenübersicht" : "Weiter");
  $("family-tour").hidden = false;
  $("family-tour").dataset.step = String(tourStep);
  const target = document.querySelector(selector);
  target.classList.add("tour-target");
  let startHighlights = () => {};
  if (!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
    const highlights = tourStep === 3
      ? [document.querySelector(".compiled-title h3"), $("compile-button")]
      : tourStep === 4 ? [$("notes-heading"), $("note-form")]
      : tourStep === 0 ? [$("library-title"), $("new-person-button")]
      : tourStep === 1 ? [$("voice-title"), ...document.querySelectorAll(".voice-choice-options label")] : [];
    const playHighlights = () => {
      if (document.hidden || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
      const bounds = target.getBoundingClientRect();
      const surface = scrollSurface();
      const visible = surface === window ? { top: 0, bottom: window.innerHeight } : surface.getBoundingClientRect();
      if (bounds.height > 0 && (bounds.bottom < visible.top || bounds.top > visible.bottom)) return;
      tourAnimations.forEach((animation) => animation.cancel());
      tourAnimations = [];
      tourTimers.forEach(clearTimeout);
      tourTimers = [];
      highlights.forEach((element, index) => {
      if (typeof element.animate !== "function") return;
      const peak = element.closest(".voice-choice") ? 1.08 : element.id === "note-form" ? 1.04 : element.id === "compile-button" ? 1.28 : 1.16;
      tourAnimations.push(element.animate([
        { transform: "translateY(0) scale(1)", offset: 0, easing: "cubic-bezier(.4, 0, .2, 1)" },
        { transform: `translateY(-4px) scale(${peak})`, offset: .45, easing: "cubic-bezier(.4, 0, .2, 1)" },
        { transform: "translateY(0) scale(1)", offset: 1 },
      ], { duration: 1000, delay: 240 + index * 420, easing: "linear" }));
    });
    if (tourStep === 0) {
      const demo = document.querySelector('[data-person-id="tour-person"]');
      if (demo) {
        for (const [delay, selected] of [[1300, true], [2800, false]]) {
          tourTimers.push(setTimeout(() => {
            if (tourStep !== 0 || !demo.isConnected || document.hidden) return;
            tourPersonSelected = selected;
            updatePersonSelection(demo, tourPerson, selected);
          }, delay));
        }
      }
    }
    };
    startHighlights = () => {
      playHighlights();
      if (highlights.length || tourStep === 0) tourLoop = setInterval(playHighlights, 5000);
    };
  }
  alignTourSection(!instant, () => {
    startHighlights();
    $("tour-next").focus({ preventScroll: true });
  });
}
function scrollTourTo(top, smooth, onArrive = () => {}) {
  cancelTourScroll?.();
  const surface = scrollSurface();
  const start = scrollPosition();
  const distance = top - start;
  if (!smooth || Math.abs(distance) < 2 || !window.requestAnimationFrame || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
    surface.scrollTo({ top, behavior: "instant" });
    onArrive();
    return;
  }
  const duration = Math.min(1500, 900 + Math.abs(distance) * .25);
  let frame, started;
  $("tour-next").disabled = true;
  const cleanup = () => {
    cancelAnimationFrame(frame);
    window.removeEventListener("wheel", interrupt);
    window.removeEventListener("touchstart", interrupt);
    window.removeEventListener("keydown", interruptKey);
    document.removeEventListener("visibilitychange", visibility);
    $("tour-next").disabled = false;
    cancelTourScroll = null;
  };
  const interrupt = () => { cleanup(); onArrive(); };
  const interruptKey = (event) => { if (["ArrowDown", "ArrowUp", "PageDown", "PageUp", "Home", "End", " "].includes(event.key)) interrupt(); };
  const visibility = () => { if (document.hidden) interrupt(); };
  cancelTourScroll = cleanup;
  window.addEventListener("wheel", interrupt, { passive: true });
  window.addEventListener("touchstart", interrupt, { passive: true });
  window.addEventListener("keydown", interruptKey);
  document.addEventListener("visibilitychange", visibility);
  const tick = (time) => {
    started ??= time;
    const progress = Math.min(1, (time - started) / duration);
    const eased = (1 - Math.cos(Math.PI * progress)) / 2;
    surface.scrollTo({ top: start + distance * eased, behavior: "instant" });
    if (progress < 1) frame = requestAnimationFrame(tick);
    else { cleanup(); onArrive(); }
  };
  frame = requestAnimationFrame(tick);
}
function alignTourSection(smooth = false, onArrive = () => {}) {
  const target = document.querySelector(".tour-target");
  if (tourStep < 0 || !target) return;
  // Measure the whole subject, not just the heading that receives the pop.
  const selectors = ["#library-view .page-head, #person-grid, .person-add-row", ".voice-section", ".editor-heading, .profile-panel", ".compiled-card", ".notes-panel"];
  const rects = [...document.querySelectorAll(selectors[tourStep])]
    .map(element => element.getBoundingClientRect()).filter(rect => rect.height > 0);
  const section = { top: Math.min(...rects.map(rect => rect.top)), bottom: Math.max(...rects.map(rect => rect.bottom)) };
  const surface = scrollSurface();
  const viewport = surface === window ? { top: tourScrollInset() - 24, bottom: window.innerHeight } : surface.getBoundingClientRect();
  const card = $("family-tour").getBoundingClientRect();
  const visible = { top: viewport.top, bottom: Math.min(viewport.bottom, card.top) };
  const top = tourScrollDestination(section, visible, scrollPosition());
  scrollTourTo(top, smooth, onArrive);
}
function tourScrollDestination(section, visible, currentScroll) {
  const margin = 24;
  const available = Math.max(0, visible.bottom - visible.top - margin * 2);
  const height = section.bottom - section.top;
  const inset = margin + Math.max(0, (available - height) / 2);
  return Math.max(0, currentScroll + section.top - visible.top - inset);
}
window.addEventListener("resize", () => { if (!cancelTourScroll) alignTourSection(); });
function animateBook(opening, source, navigate, targetSelector, complete = () => {}, enabled = true) {
  bookTransition?.();
  const content = $("family-content");
  const viewport = content.getBoundingClientRect();
  const bounds = element => {
    const rect = element?.getBoundingClientRect();
    if (!rect?.width || !rect.height) return null;
    const top = Math.max(rect.top, viewport.top), bottom = Math.min(rect.bottom, viewport.bottom);
    return bottom > top ? { left: rect.left, top, width: rect.width, height: bottom - top } : null;
  };
  const from = bounds(source);
  const coverColor = source ? getComputedStyle(source).backgroundColor : "#dff0e3";
  const cover = opening && source ? source.cloneNode(true) : null;
  bookNavigating = true;
  try { navigate(); } finally { bookNavigating = false; }
  const target = document.querySelector(targetSelector);
  const to = bounds(target);
  if (!enabled || !from || !to || typeof target?.animate !== "function" || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) { complete(); return; }
  const cardBounds = opening ? from : to;
  const pageBounds = opening ? to : from;
  const stage = document.createElement("div");
  stage.className = "book-transition-stage";
  stage.setAttribute("aria-hidden", "true");
  Object.assign(stage.style, { left: `${viewport.left}px`, top: `${viewport.top}px`, width: `${viewport.width}px`, height: `${viewport.height}px` });
  const paper = document.createElement("div");
  paper.className = "book-transition-paper";
  Object.assign(paper.style, { left: `${cardBounds.left - viewport.left}px`, top: `${cardBounds.top - viewport.top}px`, width: `${cardBounds.width}px`, height: `${cardBounds.height}px` });
  const lid = cover || target.cloneNode(true);
  lid.className = "book-transition-cover";
  lid.style.backgroundColor = opening ? coverColor : getComputedStyle(target).backgroundColor;
  lid.removeAttribute("id");
  lid.querySelectorAll("[id]").forEach(element => element.removeAttribute("id"));
  lid.querySelectorAll("button").forEach(element => { element.tabIndex = -1; });
  paper.append(lid); stage.append(paper); document.body.append(stage);
  const originalVisibility = target.style.visibility;
  const originalInert = content.inert;
  target.style.visibility = "hidden";
  content.inert = true;
  $("family-tour").classList.add("tour-morphing");
  const transform = `translate(${pageBounds.left - cardBounds.left}px, ${pageBounds.top - cardBounds.top}px) scale(${pageBounds.width / cardBounds.width}, ${pageBounds.height / cardBounds.height})`;
  const animations = [
    paper.animate(opening ? [{ transform: "none" }, { transform }] : [{ transform }, { transform: "none" }], { duration: 360, delay: opening ? 220 : 0, easing: "cubic-bezier(.32, .72, 0, 1)", fill: "both" }),
    lid.animate(opening ? [{ transform: "rotateY(0deg)", opacity: 1 }, { transform: "rotateY(-105deg)", opacity: 0 }] : [{ transform: "rotateY(-105deg)", opacity: 0 }, { transform: "rotateY(0deg)", opacity: 1 }], { duration: 300, delay: opening ? 0 : 260, easing: "cubic-bezier(.4, 0, .2, 1)", fill: "both" }),
  ];
  const cleanup = () => {
    animations.forEach(animation => animation.cancel()); stage.remove();
    target.style.visibility = originalVisibility; content.inert = originalInert;
    $("family-tour").classList.remove("tour-morphing"); bookTransition = null;
  };
  bookTransition = cleanup;
  Promise.all(animations.map(animation => animation.finished)).then(() => {
    if (bookTransition !== cleanup) return;
    cleanup();
    target.animate([{ opacity: .3 }, { opacity: 1 }], { duration: 140 });
    complete();
  }).catch(() => {});
}
function morphTourBook(opening, positioned = false) {
  if (tourMorph) return;
  const cardSelector = '[data-person-id="tour-person"]';
  const source = document.querySelector(opening ? cardSelector : ".profile-panel");
  // After choosing a voice, return gently to the booklet before opening it.
  if (opening && !positioned) {
    const surface = scrollSurface();
    const viewport = surface === window ? { top: 0, bottom: window.innerHeight } : surface.getBoundingClientRect();
    const visible = { top: viewport.top, bottom: Math.min(viewport.bottom, $("family-tour").getBoundingClientRect().top) };
    scrollTourTo(tourScrollDestination(source.getBoundingClientRect(), visible, scrollPosition()), true, () => { if (tourStep === 1) morphTourBook(true, true); });
    return;
  }
  // Bring the open booklet into view before closing it back into the overview.
  if (!opening && !positioned) {
    const heading = document.querySelector(".editor-heading");
    const top = Math.max(0, scrollPosition() + heading.getBoundingClientRect().top - tourScrollInset());
    scrollTourTo(top, true, () => { if (tourStep === 4) morphTourBook(false, true); });
    return;
  }
  animateBook(opening, source, () => { tourStep = opening ? 2 : 0; showTourStep(true); }, opening ? ".profile-panel" : cardSelector, () => {
    $("tour-next").disabled = false; tourMorph = null;
    if (opening) $("tour-next").focus({ preventScroll: true }); else finishTour();
  });
  if (bookTransition) {
    $("tour-next").disabled = true;
    tourMorph = () => { bookTransition?.(); $("tour-next").disabled = false; tourMorph = null; };
  }
}
function finishTour(create = false, navigate = true) {
  cancelTourScroll?.();
  tourMorph?.();
  clearInterval(tourLoop);
  tourLoop = null;
  tourTimers.forEach(clearTimeout);
  tourTimers = [];
  tourAnimations.forEach((animation) => animation.cancel());
  tourAnimations = [];
  tourStep = -1;
  try { localStorage.setItem(TOUR_KEY, "seen"); } catch { /* Dismiss without storage. */ }
  $("family-tour").hidden = true;
  document.querySelectorAll(".tour-target").forEach((element) => element.classList.remove("tour-target"));
  $("editor-view").querySelector(".editor-grid").inert = false;
  $("editor-back").disabled = false;
  $("delete-person-button").hidden = false;
  if (navigate) {
    if (create) addPerson();
    else { showView("library"); $("new-person-button").focus({ preventScroll: true }); }
  }
}
function showDialog(title, message, actions = null) {
  $("dialog-title").textContent = title;
  $("dialog-message").textContent = message;
  brandMentions($("dialog-title"));
  brandMentions($("dialog-message"));
  $("app-dialog").returnValue = "";
  const area = $("dialog-actions");
  area.replaceChildren();
  if (actions) {
    const cancel = document.createElement("button");
    cancel.className = "button button-quiet";
    cancel.value = "cancel";
    cancel.textContent = "Abbrechen";
    area.append(cancel);
    const okay = document.createElement("button");
    okay.className = `button ${actions.danger ? "button-danger" : "button-primary"}`;
    okay.value = "confirm";
    okay.textContent = actions.label;
    area.append(okay);
    $("app-dialog").addEventListener(
      "close",
      function onClose() {
        $("app-dialog").removeEventListener("close", onClose);
        if ($("app-dialog").returnValue === "confirm") actions.onConfirm();
      },
      { once: true },
    );
  } else {
    const okay = document.createElement("button");
    okay.className = "button button-primary";
    okay.value = "close";
    okay.textContent = "Verstanden";
    area.append(okay);
  }
  $("app-dialog").showModal();
}
function apiUnavailable(feature) {
  showDialog(
    `${feature} noch nicht verbunden`,
    "Diese Funktion braucht den Sprach- oder Modelldienst. In der Vorschau wird nichts gesendet oder berechnet.",
  );
}
async function compilePersona() {
  const person = currentPerson();
  if (!person) return;
  if (!person.notes.length) {
    showDialog("Noch keine Erinnerungen", "Haltet zuerst eine gemeinsame Erinnerung fest. Auch ein kleines Detail ist ein guter Anfang.");
    return;
  }
  const personId = person.id;
  const notes = person.notes.map((note) => note.text);
  const noteSnapshot = JSON.stringify(notes);
  const previous = person.compiled;
  const previousPassages = person.passages;
  const button = $("compile-button");
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  $("compiled-content").setAttribute("aria-busy", "true");
  try {
    const response = await fetch("api/persona", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        profile: {
          name: person.name,
          age: person.age,
          language: person.language,
          address: person.address,
          guidance: person.guidance,
          notes,
        },
      }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok)
      throw new Error(result.error || "Der Modelldienst ist noch nicht verbunden. Bitte versuchen Sie es später erneut.");
    const latest = state.people.find((item) => item.id === personId);
    if (!latest || JSON.stringify(latest.notes.map((note) => note.text)) !== noteSnapshot)
      return;
    latest.compiled = String(result.summary || "").trim().slice(0, 600);
    if (!latest.compiled) throw new Error("Das Modell lieferte keine Zusammenfassung.");
    latest.personaNeedsRefresh = false;
    latest.passages = Array.isArray(result.passages)
      ? result.passages.slice(0, 4).filter((part) => part && typeof part.title === "string" && typeof part.text === "string")
        .map((part) => ({ title: part.title.trim().slice(0, 50), text: part.text.trim().slice(0, 400) }))
        .filter((part) => part.title && part.text)
      : [];
    if (!latest.name && result.fields?.name) latest.name = String(result.fields.name).slice(0, 50);
    if (!latest.age && /^\d{1,3}$/.test(String(result.fields?.age || "")))
      latest.age = String(result.fields.age);
    persist();
    renderHome();
    if (editingId === personId) renderEditor();
  } catch (error) {
    const latest = state.people.find((item) => item.id === personId);
    if (latest) { latest.compiled = previous; latest.passages = previousPassages; }
    if (editingId === personId && latest) renderPersona(latest);
    showDialog("Aktualisierung nicht möglich", error.message || "Bitte versuchen Sie es später erneut.");
  } finally {
    button.disabled = false;
    button.removeAttribute("aria-busy");
    $("compiled-content").removeAttribute("aria-busy");
  }
}
function today() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Europe/Zurich" });
}
function dailyUsed() {
  return state.daily?.date === today()
    ? Math.max(0, Number(state.daily.used) || 0)
    : 0;
}
function setHomeStatus(message) {
  const status = $("home-status");
  status.textContent = message;
  brandMentions(status);
  status.hidden = !message;
}
function setLiveTranscript(text, partial = false) {
  const caption = $("live-transcript");
  caption.textContent = text;
  caption.hidden = !text;
  caption.classList.toggle("is-partial", partial);
}
function renderHome() {
  const people = selectedPeople();
  const names = new Intl.ListFormat("de-CH", { style: "long", type: "conjunction" }).format(people.map((person) => person.name));
  document.body.classList.toggle("needs-profile", !people.length);
  $("home-title").textContent = people.length
    ? `Hallo, ${names}.`
    : "Hallo, Wer bist du?";
  $("talk-button").innerHTML = people.length
    ? 'Sprechen <span class="icon icon-microphone" aria-hidden="true"></span>'
    : 'Für Angehörige <span class="icon icon-arrow-right" aria-hidden="true"></span>';
  $("talk-button").setAttribute(
    "aria-label",
    people.length ? "Sprechen" : "Für Angehörige öffnen",
  );
}
function stopConversation() {
  setLiveTranscript("");
  conversationRequest++;
  conversationConnecting = false;
  if (conversationState) {
    const session = conversationState;
    session.discarded = true;
    clearTimeout(session.timeout);
    clearInterval(session.silenceCheck);
    traceConversation("stopped");
    session.abort.abort();
    session.socket.close();
    session.worklet?.disconnect();
    session.source?.disconnect();
    session.context?.close().catch(() => {});
    session.stream.getTracks().forEach((track) => track.stop());
    conversationState = null;
  }
  if (replyAudio) {
    replyAudio.stop();
    replyAudio = null;
  }
  $("talk-button").disabled = false;
  $("talk-button").removeAttribute("aria-busy");
  $("talk-button").classList.remove("is-recording");
  renderHome();
}
async function startConversation() {
  if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext || !window.AudioWorkletNode || !window.WebSocket) {
    setHomeStatus("Live-Gespräche sind auf diesem Gerät oder Browser nicht verfügbar.");
    return;
  }
  const request = ++conversationRequest;
  conversationConnecting = true;
  conversationDiagnostics = [];
  traceConversation("connecting");
  setLiveTranscript("");
  setHomeStatus("Verbindung wird aufgebaut …");
  let stream;
  let context;
  let socket;
  try {
    // Unlock Web Audio in the original tap, before network and microphone prompts.
    context = new AudioContext();
    await context.resume();
    const readiness = await fetch("api/status");
    const services = await readiness.json().catch(() => ({}));
    if (!readiness.ok || !services.realtime_ready || !services.voice_ready || !services.model_ready)
      throw new Error("Das Live-Gespräch ist noch nicht vollständig eingerichtet.");
    const tokenResponse = await fetch("api/scribe-token", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
    });
    const tokenResult = await tokenResponse.json().catch(() => ({}));
    if (!tokenResponse.ok || !tokenResult.token)
      throw new Error(tokenResult.error || "Die Live-Spracherkennung ist gerade nicht erreichbar.");
    if (request !== conversationRequest) return;
    stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
    if (request !== conversationRequest) return;
    await context.audioWorklet.addModule("capture-worklet.js?v=19");
    await context.resume();
    const sampleRate = context.sampleRate;
    if (![8000, 16000, 22050, 24000, 44100, 48000].includes(sampleRate))
      throw new Error("Die Abtastrate des Mikrofons wird nicht unterstützt.");
    const params = new URLSearchParams({
      model_id: "scribe_v2_realtime",
      token: tokenResult.token,
      audio_format: `pcm_${sampleRate}`,
      commit_strategy: "vad",
      vad_silence_threshold_secs: "2.0",
      vad_threshold: "0.4",
      min_speech_duration_ms: "100",
      min_silence_duration_ms: "100",
    });
    socket = new WebSocket(`wss://api.elevenlabs.io/v1/speech-to-text/realtime?${params}`);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Verbindung zur Spracherkennung dauert zu lange.")), 12000);
      socket.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
      socket.addEventListener("error", () => { clearTimeout(timer); reject(new Error("Live-Spracherkennung nicht erreichbar.")); }, { once: true });
      socket.addEventListener("close", () => { clearTimeout(timer); reject(new Error("Live-Verbindung wurde geschlossen.")); }, { once: true });
    });
    if (request !== conversationRequest) return;
    const source = context.createMediaStreamSource(stream);
    const worklet = new AudioWorkletNode(context, "zaeme-capture");
    const session = { stream, context, socket, source, worklet, lastAudioAt: performance.now(), abort: new AbortController(), discarded: false, processing: false };
    conversationState = session;
    worklet.port.onmessage = (event) => {
      if (session.discarded || socket.readyState !== WebSocket.OPEN) return;
      session.lastAudioAt = performance.now();
      const bytes = new Uint8Array(event.data);
      let binary = "";
      for (let index = 0; index < bytes.length; index++) binary += String.fromCharCode(bytes[index]);
      const chunk = { message_type: "input_audio_chunk", audio_base_64: btoa(binary), sample_rate: sampleRate };
      socket.send(JSON.stringify(chunk));
    };
    socket.addEventListener("message", (event) => {
      if (session.discarded || request !== conversationRequest) return;
      let message;
      try { message = JSON.parse(event.data); } catch { return; }
      const words = String(message.text || "").trim();
      if (message.message_type === "partial_transcript" && !session.processing && words) {
        traceConversation("partial", { chars: words.length });
        setLiveTranscript(words, true);
      }
      if (message.message_type === "committed_transcript" && words) {
        if (!session.processing) {
          traceConversation("final", { chars: words.length });
          runConversation(words, request, session);
        } else traceConversation("final-ignored", { chars: words.length });
      }
      if (["rate_limited", "error", "auth_error", "quota_exceeded", "input_error", "invalid_request", "resource_exhausted"].includes(message.message_type) || message.message_type?.endsWith("_error")) {
        traceConversation("provider-error", { type: message.message_type });
        stopConversation();
        setHomeStatus("Die Live-Spracherkennung ist gerade nicht verfügbar. Bitte später erneut versuchen.");
      }
    });
    socket.addEventListener("close", () => {
      if (!session.discarded && request === conversationRequest) {
        stopConversation();
        setHomeStatus("Die Live-Verbindung wurde unterbrochen. Bitte erneut starten.");
      }
    });
    source.connect(worklet);
    worklet.connect(context.destination);
    session.silenceCheck = setInterval(() => {
      if (session.discarded || request !== conversationRequest || session.processing) return;
      const now = performance.now();
      if (now - session.lastAudioAt > 8000) {
        traceConversation("audio-stalled");
        stopConversation();
        setHomeStatus("Das Mikrofon wurde unterbrochen. Bitte starten Sie das Gespräch erneut.");
        return;
      }
    }, 250);
    session.timeout = setTimeout(() => {
      if (conversationState === session) {
        stopConversation();
        setHomeStatus("Das Gespräch ist nach zehn Minuten beendet. Sie können es erneut starten.");
      }
    }, 10 * 60 * 1000);
    $("talk-button").classList.add("is-recording");
    $("talk-button").textContent = "Gespräch beenden";
    $("talk-button").setAttribute("aria-label", "Gespräch beenden");
    setHomeStatus("Ich höre zu …");
    traceConversation("listening");
  } catch (error) {
    socket?.close();
    context?.close().catch(() => {});
    if (request !== conversationRequest) return;
    stopConversation();
    setHomeStatus(error.message || "Der Gesprächsdienst ist gerade nicht erreichbar.");
  } finally {
    if (request === conversationRequest) conversationConnecting = false;
    if (request !== conversationRequest && !conversationState) {
      socket?.close();
      context?.close().catch(() => {});
    }
    if (conversationState?.stream !== stream)
      stream?.getTracks().forEach((track) => track.stop());
  }
}
async function runConversation(heard, request, session) {
  session.processing = true;
  session.stream.getAudioTracks().forEach((track) => { track.enabled = false; });
  setLiveTranscript(heard);
  setHomeStatus("Ich überlege kurz …");
  try {
    const people = selectedPeople();
    if (!people.length) { stopConversation(); return; }
    const groupId = JSON.stringify(people.map((person) => person.id).sort());
    if (conversationPersonId !== groupId) {
      conversationPersonId = groupId;
      conversationMessages = [];
    }
    const messages = [...conversationMessages, { role: "user", content: heard }];
    traceConversation("model-request", { chars: heard.length });
    const chatResponse = await fetch("api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        profiles: people.map((person) => ({
          name: person.name,
          age: person.age,
          language: person.language,
          address: person.address,
          guidance: person.guidance,
          compiled: person.compiled,
        })),
        messages,
      }),
      signal: session.abort.signal,
    });
    const chatResult = await chatResponse.json().catch(() => ({}));
    if (!chatResponse.ok) throw new Error(chatResult.error || "Gespräch gerade nicht verfügbar.");
    const answer = String(chatResult.response || "").trim().slice(0, 600);
    if (!answer) throw new Error("Es kam keine Antwort. Bitte versuchen Sie es erneut.");
    if (request !== conversationRequest) return;
    traceConversation("model-reply", { chars: answer.length });
    conversationMessages = [...messages, { role: "assistant", content: answer }].slice(-8);
    state.daily = { date: today(), used: dailyUsed() + 1 };
    persist();
    setHomeStatus(answer);
    const speechResponse = await fetch("api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: answer, voice: state.voiceGender }),
      signal: session.abort.signal,
    });
    if (!speechResponse.ok) throw new Error("Die Antwort steht hier als Text. Die Stimme ist gerade nicht verfügbar.");
    const spoken = await speechResponse.blob();
    if (request !== conversationRequest) return;
    const decoded = await session.context.decodeAudioData(await spoken.arrayBuffer());
    if (request !== conversationRequest) return;
    const playback = session.context.createBufferSource();
    playback.buffer = decoded;
    playback.connect(session.context.destination);
    replyAudio = playback;
    playback.addEventListener("ended", () => {
      if (replyAudio === playback) replyAudio = null;
      if (!session.discarded && request === conversationRequest) {
        if (dailyUsed() >= LIMITS.conversationsPerDay) {
          stopConversation();
          setHomeStatus(`Das Gastlimit von ${LIMITS.conversationsPerDay} Gesprächsbeiträgen für heute ist erreicht.`);
          return;
        }
        session.processing = false;
        session.lastAudioAt = performance.now();
        session.stream.getAudioTracks().forEach((track) => { track.enabled = true; });
        setHomeStatus("Ich höre zu …");
        traceConversation("listening");
      }
    }, { once: true });
    playback.start();
    traceConversation("reply-playing");
  } catch (error) {
    if (request === conversationRequest) {
      setHomeStatus(error.message || "Bitte versuchen Sie es erneut.");
      session.processing = false;
      session.lastAudioAt = performance.now();
      session.stream.getAudioTracks().forEach((track) => { track.enabled = true; });
      traceConversation("turn-error", { type: error.name || "Error" });
    }
  }
}
function renderLibrary() {
  document.querySelector(`input[name="voice-gender"][value="${state.voiceGender}"]`).checked = true;
  const grid = $("person-grid");
  grid.replaceChildren();
  $("library-home-label").textContent = selectedPeople().length
    ? "Zum Gespräch"
    : "Zur Startseite";
  const atLimit = state.people.length >= LIMITS.people;
  $("new-person-button").hidden = atLimit;
  $("person-limit-message").hidden = !atLimit;
  const showingDemo = tourStep >= 0 && tourStep < 2 && !state.people.length;
  if (!state.people.length && !showingDemo) {
    const empty = document.createElement("div");
    empty.className = "person-empty";
    const title = document.createElement("h2");
    title.textContent = "Noch keine Person hier.";
    const detail = document.createElement("p");
    detail.textContent = "Ein neues Profil bietet Platz für eure gemeinsamen Erinnerungen.";
    empty.append(title, detail);
    grid.append(empty);
    return;
  }
  const orderedPeople = showingDemo ? [tourPerson] : [...state.people].sort(
    (a, b) =>
      Number(state.selectedIds.includes(b.id)) - Number(state.selectedIds.includes(a.id)),
  );
  for (const person of orderedPeople) {
    const card = document.createElement("article");
    const demo = person === tourPerson;
    const selected = demo ? tourPersonSelected : state.selectedIds.includes(person.id);
    card.dataset.personId = person.id;
    card.className = `person-card${selected ? " is-selected" : ""}`;
    const select = document.createElement("button");
    select.className = "person-select";
    select.type = "button";
    select.setAttribute("aria-pressed", String(selected));
    select.setAttribute(
      "aria-label",
      `${person.name || "Neue Person"} ${selected ? "aus dem Gespräch entfernen" : "ins Gespräch aufnehmen"}`,
    );
    const title = document.createElement("h3");
    title.textContent = person.name || "Neue Person";
    const subtitle = document.createElement("p");
    subtitle.textContent = `${person.notes.length} ${person.notes.length === 1 ? "Erinnerung" : "Erinnerungen"} · ${person.language || "Schweizerdeutsch"}${person.sample ? " · Beispiel" : ""}`;
    const initial = document.createElement("span");
    initial.className = "person-initial";
    initial.setAttribute("aria-hidden", "true");
    initial.textContent = (person.name || "?").slice(0, 1).toUpperCase();
    const check = document.createElement("span");
    check.className = "person-selection";
    check.setAttribute("aria-hidden", "true");
    check.innerHTML = '<span class="icon icon-check"></span>';
    select.append(initial, title, subtitle, check);
    select.addEventListener("click", () => {
      const nextSelected = !(demo ? tourPersonSelected : state.selectedIds.includes(person.id));
      if (demo) {
        tourTimers.forEach(clearTimeout);
        tourTimers = [];
        tourPersonSelected = nextSelected;
        updatePersonSelection(card, person, nextSelected);
        return;
      }
      setSelection(nextSelected ? [...state.selectedIds, person.id] : state.selectedIds.filter((id) => id !== person.id));
      persist();
      renderLibrary();
      renderHome();
      [...grid.querySelectorAll(".person-card")].find((item) => item.dataset.personId === person.id)?.querySelector(".person-select").focus({ preventScroll: true });
    });
    const edit = document.createElement("button");
    edit.className = "icon-button person-edit";
    edit.type = "button";
    edit.setAttribute(
      "aria-label",
      `${person.name || "Neue Person"} bearbeiten`,
    );
    edit.title = "Profil bearbeiten";
    edit.innerHTML = '<span class="icon icon-edit" aria-hidden="true"></span>';
    edit.addEventListener("click", (event) => {
      if (demo) morphTourBook(true);
      else openPerson(person.id, event.detail !== 0);
    });
    card.append(select, edit);
    grid.append(card);
  }
}
function updatePersonSelection(card, person, selected) {
  card.classList.toggle("is-selected", selected);
  const button = card.querySelector(".person-select");
  button.setAttribute("aria-pressed", String(selected));
  button.setAttribute("aria-label", `${person.name || "Neue Person"} ${selected ? "aus dem Gespräch entfernen" : "ins Gespräch aufnehmen"}`);
}
function addPerson() {
  if (tourStep >= 0) finishTour(false, false);
  if (state.people.length >= LIMITS.people) {
    showDialog(
      "Gastlimit erreicht",
      `Im Gastmodus können Sie ${LIMITS.people} Personen auf diesem Gerät speichern. Eine Anmeldung mit mehr Profilen folgt in einer späteren Version.`,
    );
    return;
  }
  const person = {
    id: makeId(),
    name: "",
    age: "",
    language: "Schweizerdeutsch",
    address: "Sie",
    guidance: "",
    compiled: null,
    sample: false,
    notes: [],
  };
  state.people.push(person);
  setSelection([...state.selectedIds, person.id]);
  persist();
  openPerson(person.id);
}
function openPerson(id, animate = true) {
  const source = [...document.querySelectorAll(".person-card")].find(card => card.dataset.personId === id);
  libraryScroll = scrollPosition();
  editingId = id;
  noteEditingId = null;
  $("note-text").value = "";
  $("save-note-button").setAttribute("aria-label", "Erinnerung speichern");
  updateComposerSave();
  setComposerStatus("");
  animateBook(true, source, () => showView("editor"), ".profile-panel", () => $("editor-back").focus({ preventScroll: true }), animate);
}
function closePerson(animate = true) {
  const id = editingId;
  animateBook(false, document.querySelector(".profile-panel"), () => {
    showView("library"); scrollSurface().scrollTo({ top: libraryScroll, behavior: "instant" });
  }, `[data-person-id="${id}"]`, () => document.querySelector(`[data-person-id="${id}"] .person-edit`)?.focus({ preventScroll: true }), animate);
}
function renderEditor() {
  const person = currentPerson();
  if (!person) {
    showView("library");
    return;
  }
  $("editor-title").textContent = person.name || (person === tourPerson ? "Neue Person" : "Neues Profil");
  $("field-name").value = person.name || "";
  $("field-age").value = person.age || "";
  $("field-language").value = person.language || "Schweizerdeutsch";
  $("field-address").value = person.address || "Sie";
  $("field-guidance").value = person.guidance || "";
  renderPersona(person);
  const list = $("notes-list");
  const previousPositions = new Map([...list.querySelectorAll(".note-card")]
    .map((card) => [card.dataset.noteId, card.getBoundingClientRect().top]));
  list.replaceChildren();
  if (!person.notes.length) {
    const empty = document.createElement("div");
    empty.className = "note-empty";
    empty.textContent =
      "Welche Erinnerung verbindet euch? Auch ein kleines Detail findet hier Platz.";
    list.append(empty);
    return;
  }
  const ordered = [...person.notes]
    .reverse()
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  for (const note of ordered) {
    const card = document.createElement("article");
    card.className = "note-card";
    card.dataset.noteId = note.id;
    const top = document.createElement("div");
    top.className = "note-card-top";
    const date = document.createElement("span");
    date.className = "note-date";
    date.textContent = new Date(note.createdAt).toLocaleDateString("de-CH", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
    top.append(date);
    const content = document.createElement("p");
    content.id = `memory-${note.id}`;
    content.textContent = note.text;
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "note-toggle";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Erinnerung öffnen");
    toggle.setAttribute("aria-describedby", content.id);
    toggle.setAttribute("aria-controls", content.id);
    toggle.append(content);
    toggle.addEventListener("click", (event) => toggleMemory(card, toggle, event.detail === 0));
    card.addEventListener("click", (event) => {
      if (!event.target.closest("button")) toggleMemory(card, toggle);
    });
    card.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        toggleMemory(card, toggle, true);
        toggle.focus();
      }
    });
    const actions = document.createElement("div");
    actions.className = "note-card-actions";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "icon-button note-edit";
    edit.setAttribute("aria-label", "Erinnerung bearbeiten");
    edit.title = "Erinnerung bearbeiten";
    edit.innerHTML = '<span class="icon icon-edit" aria-hidden="true"></span>';
    edit.addEventListener("click", () => editNote(note.id));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "icon-button delete-note";
    remove.setAttribute("aria-label", "Erinnerung löschen");
    remove.title = "Erinnerung löschen";
    remove.innerHTML =
      '<span class="icon icon-trash" aria-hidden="true"></span>';
    remove.addEventListener("click", () => deleteNote(note.id));
    actions.append(edit, remove);
    top.append(actions);
    card.append(top, toggle);
    list.append(card);
    card.classList.toggle("is-truncated", content.scrollHeight > 92);
    if (
      note.id === lastAddedNoteId &&
      typeof card.animate === "function" &&
      !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
    ) {
      card.animate(
        [
          { opacity: .2, transform: "translateY(-32px) scale(0.96) rotate(-1deg)" },
          { opacity: 1, transform: "translateY(0) scale(1) rotate(0)" },
        ],
        {
          duration: 280,
          easing: "cubic-bezier(0.22, 1.15, 0.36, 1)",
        },
      );
    } else if (note.id === lastAddedNoteId) {
      card.classList.add("is-entering");
      card.addEventListener("animationend", () => card.classList.remove("is-entering"), { once: true });
    }
    const previousTop = previousPositions.get(note.id);
    if (lastAddedNoteId && previousTop !== undefined && typeof card.animate === "function" && !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      const distance = previousTop - card.getBoundingClientRect().top;
      if (distance) card.animate([{ transform: `translateY(${distance}px)` }, { transform: "translateY(0)" }], { duration: 280, easing: "cubic-bezier(.23, 1, .32, 1)" });
    }
  }
  lastAddedNoteId = null;
}
function renderPersona(person) {
  const needsRefresh = person.notes.length > 0 && (person.personaNeedsRefresh || !person.compiled);
  $("compile-button").classList.toggle("needs-refresh", Boolean(needsRefresh));
  $("compile-button").setAttribute("aria-label", needsRefresh ? "Neue oder geänderte Erinnerungen: Zusammenfassung aktualisieren" : "Zusammenfassung aktualisieren");
  const container = $("compiled-content");
  container.replaceChildren();
  const passages = Array.isArray(person.passages) && person.passages.length
    ? person.passages
    : person.compiled ? [{ title: "Meine Geschichte", text: person.compiled }] : [];
  if (!passages.length) {
    const empty = document.createElement("p");
    empty.className = "compiled-empty";
    empty.textContent = "Was ich mag, was mir wichtig ist und was mich ausmacht – hier finden eure Erinnerungen zusammen.";
    container.append(empty);
    return;
  }
  for (const passage of passages) {
    const section = document.createElement("section");
    section.className = "persona-passage";
    const heading = document.createElement("h4");
    heading.textContent = passage.title;
    const text = document.createElement("p");
    text.textContent = passage.text;
    section.append(heading, text);
    container.append(section);
  }
}
function toggleMemory(card, button, keyboard = false) {
  clearTimeout(card.closeTimer);
  const opening = button.getAttribute("aria-expanded") !== "true";
  button.setAttribute("aria-expanded", String(opening));
  button.setAttribute("aria-label", opening ? "Erinnerung schliessen" : "Erinnerung öffnen");
  const reduced = keyboard || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  card.style.transitionDuration = reduced ? "0ms" : "";
  if (opening) {
    card.classList.remove("is-closing");
    card.classList.add("is-expanded");
    sizeExpandedMemory(card);
  } else {
    card.classList.add("is-closing");
    card.style.height = "184px";
    const finish = () => {
      card.classList.remove("is-expanded", "is-closing");
      card.style.height = "";
    };
    if (reduced) finish();
    else card.closeTimer = setTimeout(finish, 250);
  }
}
function sizeExpandedMemory(card) {
  const text = card.querySelector("p");
  const top = card.querySelector(".note-card-top");
  const spacing = window.innerWidth <= 600 ? 78 : 51;
  card.style.height = `${Math.max(184, top.offsetHeight + text.scrollHeight + spacing)}px`;
}
window.addEventListener("resize", () => {
  for (const card of document.querySelectorAll(".note-card")) {
    card.classList.toggle("is-truncated", card.querySelector("p").scrollHeight > 92);
    if (card.classList.contains("is-expanded") && !card.classList.contains("is-closing")) sizeExpandedMemory(card);
  }
});
function saveFields() {
  const person = currentPerson();
  if (!person) return;
  person.name = $("field-name").value.trim().slice(0, 50);
  person.age =
    $("field-age").value &&
    Number($("field-age").value) >= 1 &&
    Number($("field-age").value) <= 120
      ? $("field-age").value
      : "";
  person.language = $("field-language").value;
  person.address = $("field-address").value;
  person.guidance = $("field-guidance").value.trim().slice(0, 500);
  person.sample = false;
  persist();
  $("editor-title").textContent = person.name || "Neues Profil";
  renderHome();
}
function invalidateCompiled(person) {
  person.personaNeedsRefresh = true;
  person.compiled = null;
  person.passages = [];
  renderPersona(person);
}
function addOrUpdateNote(event) {
  event.preventDefault();
  const person = currentPerson();
  if (!person) return;
  const value = $("note-text").value.trim();
  if (!value) return;
  if (noteEditingId) {
    const note = person.notes.find((item) => item.id === noteEditingId);
    if (note) note.text = value.slice(0, 500);
    noteEditingId = null;
  } else {
    if (person.notes.length >= LIMITS.notes) {
      const oldest = [...person.notes].sort(
        (a, b) => new Date(a.createdAt) - new Date(b.createdAt),
      )[0];
      person.notes = person.notes.filter((item) => item.id !== oldest.id);
      setComposerStatus(
        "Die älteste Erinnerung wurde entfernt, um Platz zu schaffen.",
      );
    } else setComposerStatus("");
    const id = makeId();
    person.notes.push({
      id,
      text: value.slice(0, 500),
      createdAt: new Date().toISOString(),
    });
    lastAddedNoteId = id;
  }
  person.sample = false;
  invalidateCompiled(person);
  persist();
  $("note-text").value = "";
  $("save-note-button").setAttribute("aria-label", "Erinnerung speichern");
  updateComposerSave();
  renderEditor();
}
function editNote(id) {
  const note = currentPerson()?.notes.find((item) => item.id === id);
  if (!note) return;
  noteEditingId = id;
  $("note-text").value = note.text;
  $("save-note-button").setAttribute("aria-label", "Änderung speichern");
  updateComposerSave();
  $("note-text").focus();
  $("note-text").scrollIntoView({ behavior: "smooth", block: "center" });
}
function deleteNote(id) {
  showDialog(
    "Erinnerung löschen?",
    "Diese Erinnerung wird von diesem Gerät gelöscht. Die bisherige Zusammenfassung wird ebenfalls entfernt, damit sie die Erinnerung nicht weiter enthält.",
    {
      danger: true,
      label: "Löschen",
      onConfirm: () => {
        const person = currentPerson();
        if (!person) return;
        person.notes = person.notes.filter((note) => note.id !== id);
        invalidateCompiled(person);
        persist();
        renderEditor();
      },
    },
  );
}
function deletePerson() {
  const person = currentPerson();
  if (!person) return;
  showDialog(
    `${person.name || "Diese Person"} löschen?`,
    "Das Profil und alle zugehörigen Erinnerungen werden dauerhaft aus diesem Browser entfernt. Das kann nicht rückgängig gemacht werden.",
    {
      danger: true,
      label: "Profil löschen",
      onConfirm: () => {
        state.people = state.people.filter((item) => item.id !== person.id);
        setSelection(state.selectedIds.filter((id) => id !== person.id));
        editingId = null;
        persist();
        showView("library");
      },
    },
  );
}
function setComposerStatus(message) {
  const status = $("note-form-hint");
  status.textContent = message;
  status.hidden = !message;
}
function updateComposerSave() {
  $("save-note-button").disabled = !$("note-text").value.trim();
}
function showRecordingStage(stage) {
  $("compose-idle").hidden = stage !== "idle";
  $("recording-panel").hidden = stage !== "recording";
  $("transcribing-panel").hidden = stage !== "transcribing";
}
function stopRecordingMedia(session) {
  if (session.animationFrame) cancelAnimationFrame(session.animationFrame);
  session.stream.getTracks().forEach((track) => track.stop());
  session.audioContext?.close();
}
function drawWaveform(session) {
  const bars = $("recording-waveform").children;
  if (session.analyser) {
    const levels = new Uint8Array(session.analyser.frequencyBinCount);
    session.analyser.getByteFrequencyData(levels);
    for (let i = 0; i < bars.length; i++) {
      const level = levels[Math.floor((i / bars.length) * levels.length)] / 255;
      bars[i].style.transform =
        `scaleY(${Math.max(0.14, Math.min(1, level * 2.5))})`;
    }
  }
  session.animationFrame = requestAnimationFrame(() => drawWaveform(session));
}
async function startRecording() {
  if (recordingState) return;
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    setComposerStatus("Auf diesem Gerät ist keine Mikrofonaufnahme verfügbar.");
    return;
  }
  const request = ++recordingRequest;
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (
      request !== recordingRequest ||
      $("editor-view").classList.contains("hidden")
    ) {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    const recorder = new MediaRecorder(stream);
    const session = {
      stream,
      recorder,
      chunks: [],
      animationFrame: null,
      discarded: false,
    };
    recordingState = session;
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size) session.chunks.push(event.data);
    });
    recorder.addEventListener("stop", () => {
      stopRecordingMedia(session);
      if (session.discarded) return;
      const audio = new Blob(session.chunks, {
        type: recorder.mimeType || "audio/webm",
      });
      transcribeRecording(audio, session);
    });
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
      session.audioContext = new AudioContext();
      const source = session.audioContext.createMediaStreamSource(stream);
      session.analyser = session.audioContext.createAnalyser();
      session.analyser.fftSize = 128;
      source.connect(session.analyser);
    } else $("recording-waveform").classList.add("waveform-fallback");
    recorder.start();
    setComposerStatus("");
    showRecordingStage("recording");
    drawWaveform(session);
  } catch {
    if (recordingState) {
      stopRecordingMedia(recordingState);
      recordingState = null;
    } else stream?.getTracks().forEach((track) => track.stop());
    showRecordingStage("idle");
    setComposerStatus(
      "Mikrofon nicht verfügbar. Bitte erlauben Sie den Zugriff und versuchen Sie es erneut.",
    );
  }
}
function discardRecording() {
  const session = recordingState;
  if (!session) return;
  session.discarded = true;
  recordingState = null;
  if (session.recorder.state !== "inactive") session.recorder.stop();
  else stopRecordingMedia(session);
  showRecordingStage("idle");
  setComposerStatus("");
}
function confirmRecording() {
  const session = recordingState;
  if (!session) return;
  showRecordingStage("transcribing");
  if (session.recorder.state !== "inactive") session.recorder.stop();
}
async function transcribeRecording(audio, session) {
  if (!audio.size) {
    recordingState = null;
    showRecordingStage("idle");
    setComposerStatus("Die Aufnahme war leer. Bitte versuchen Sie es erneut.");
    return;
  }
  try {
    const form = new FormData();
    const extension = audio.type.includes("mp4") ? "m4a" : "webm";
    form.append("audio", audio, `erinnerung.${extension}`);
    const response = await fetch("api/transcribe", {
      method: "POST",
      body: form,
    });
    if (!response.ok) {
      const failure = await response.json().catch(() => ({}));
      throw new Error(
        failure.error ||
          "Notieren ist gerade nicht erreichbar. Bitte versuchen Sie es später erneut.",
      );
    }
    const result = await response.json();
    const text = String(result.text || "").trim();
    if (!text) throw new Error("empty transcript");
    if (session.discarded) return;
    const composer = $("note-text");
    composer.value = [composer.value.trim(), text]
      .filter(Boolean)
      .join("\n")
      .slice(0, 500);
    updateComposerSave();
    setComposerStatus("");
    composer.focus();
  } catch (error) {
    if (!session.discarded)
      setComposerStatus(
        `${error.message || "Notieren ist gerade nicht erreichbar."} Die Aufnahme wurde nicht gespeichert.`,
      );
  } finally {
    if (!session.discarded) {
      recordingState = null;
      showRecordingStage("idle");
    }
  }
}
for (let i = 0; i < 29; i++) {
  const bar = document.createElement("span");
  bar.style.setProperty("--index", String(i));
  $("recording-waveform").append(bar);
}
document.querySelectorAll("[data-view]").forEach((button) =>
  button.addEventListener("click", (event) => {
    event.preventDefault();
    if (button.dataset.view === "library" && !$("editor-view").classList.contains("hidden") && tourStep < 0) closePerson(event.detail !== 0);
    else showView(button.dataset.view);
  }),
);
$("new-person-button").addEventListener("click", addPerson);
$("tour-next").addEventListener("click", () => {
  if (tourStep === 4) morphTourBook(false);
  else if (tourStep === 1) morphTourBook(true);
  else { tourStep++; showTourStep(); }
});
$("tour-skip").addEventListener("click", () => finishTour());
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && tourStep >= 0) finishTour();
  else if (event.key === "Escape" && !$("family-overlay").hidden && !$("app-dialog").open) showView("home");
  if (event.key === "Tab" && !$("family-overlay").hidden && !$("app-dialog").open) {
    const controls = [...$("family-overlay").querySelectorAll('button:not(:disabled), a[href], input, textarea, select')].filter(el => !el.closest('[inert]') && el.getClientRects().length);
    const first = controls[0], last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }
});
$("editor-back").addEventListener("click", event => closePerson(event.detail !== 0));
$("delete-person-button").addEventListener("click", deletePerson);
for (const id of [
  "field-name",
  "field-age",
  "field-language",
  "field-address",
  "field-guidance",
])
  $(id).addEventListener("input", saveFields);
$("note-form").addEventListener("submit", addOrUpdateNote);
$("note-text").addEventListener("input", updateComposerSave);
$("record-note-button").addEventListener("click", startRecording);
$("discard-recording").addEventListener("click", discardRecording);
$("confirm-recording").addEventListener("click", confirmRecording);
$("compile-button").addEventListener("click", () =>
  showDialog(
    "Wer bin ich?",
    "Sollen eure gemeinsamen Erinnerungen neu zusammengefasst werden? So kann Zäme auch die neuen und geänderten Einträge im Gespräch berücksichtigen.",
    {
      label: "Aktualisieren",
      onConfirm: compilePersona,
    },
  ),
);
$("talk-button").addEventListener("click", () => {
  if (!selectedPeople().length) {
    showView("library");
    return;
  }
  if (conversationState || conversationConnecting) {
    stopConversation();
    setHomeStatus("Gespräch beendet.");
    return;
  }
  if (replyAudio) {
    replyAudio.stop();
    replyAudio = null;
  }
  if (dailyUsed() >= LIMITS.conversationsPerDay) {
    setHomeStatus(
      `Das Gastlimit von ${LIMITS.conversationsPerDay} Gesprächen für heute ist erreicht.`,
    );
    return;
  }
  startConversation();
});
for (const choice of document.querySelectorAll('input[name="voice-gender"]')) {
  choice.addEventListener("change", () => {
    state.voiceGender = choice.value;
    persist();
  });
}
window.addEventListener("pagehide", stopConversation);
$("login-button").addEventListener("click", () =>
  showDialog(
    "Anmeldung folgt",
    "In dieser Vorschau gibt es noch keine Konten. Sie können ohne Anmeldung bis zu drei Personen und je zwölf Erinnerungen lokal auf diesem Gerät speichern. Eine spätere Version soll mehrere synchronisierte Profile anbieten.",
  ),
);
$("donate-button").addEventListener("click", () =>
  showDialog(
    "Spenden noch nicht möglich",
    "TWINT ist in dieser Vorschau nicht verbunden. Es wird keine Zahlung ausgelöst. Sobald eine geprüfte Organisation und eine nachvollziehbare Kostenrechnung bereitstehen, soll hier der echte Spendenweg erscheinen.",
  ),
);
showView("home");
updateComposerSave();
const familyContent = document.createElement("div");
familyContent.id = "family-content";
familyContent.className = "family-content";
$("family-panel").append(familyContent);
for (const selector of ["#library-view", "#editor-view", "#donate-view", ".site-footer"]) familyContent.append(document.querySelector(selector));
$("family-panel").append($("family-tour"));
brandMentions(document.querySelector("main"));
brandMentions($("family-panel"));
