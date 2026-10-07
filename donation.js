/* Public totals or explicitly labelled demo amounts only. No personal data or keys. */
(() => {
  const byId = (id) => document.getElementById(id);
  const safeUrl = (value, github = false) => {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && (!github || url.hostname === "github.com") ? url.href : null;
    } catch { return null; }
  };
  const money = (value) => `CHF ${new Intl.NumberFormat("de-CH", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)}`;
  const amount = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;
  fetch("donation.json", { cache: "no-store" }).then((response) => {
    if (!response.ok) throw new Error("Donation configuration unavailable");
    return response.json();
  }).then((config) => {
    const paymentUrl = safeUrl(config.payment_url);
    if (paymentUrl && config.budget?.demo !== true) {
      const button = byId("donate-button");
      button.disabled = false;
      // Capture prevents the prototype's older placeholder dialog from opening.
      button.addEventListener("click", (event) => {
        event.stopImmediatePropagation();
        window.open(paymentUrl, "_blank", "noopener,noreferrer");
      }, { capture: true });
      byId("donation-payment-note").textContent = "Die Zahlung öffnet sich beim Zahlungsanbieter.";
    }
    const githubUrl = safeUrl(config.github_url, true);
    if (githubUrl) {
      byId("donation-github").href = githubUrl;
      byId("donation-github").hidden = false;
      byId("donation-source-note").hidden = true;
    }
    const budget = config.budget || {};
    const demo = budget.demo === true;
    const verifiedAt = new Date(budget.verified_at || "");
    if (!demo && !Number.isFinite(verifiedAt.getTime())) return;
    if (demo) byId("donation-budget-title").textContent = "Unser Budget · Demo";
    for (const [field, id] of [["donated_chf", "income"], ["hosting_chf", "hosting"], ["ai_chf", "ai"], ["speech_chf", "speech"]]) {
      if (amount(budget[field])) byId(`donation-${id}`).textContent = money(budget[field]);
    }
    const costs = [budget.hosting_chf, budget.ai_chf, budget.speech_chf];
    if (costs.every(amount)) {
      const spent = costs.reduce((sum, cost) => sum + cost, 0);
      byId("donation-expenses").textContent = money(spent);
      if (amount(budget.donated_chf)) {
        const max = Math.max(budget.donated_chf, spent, 1);
        byId("donation-income-bar").style.width = `${budget.donated_chf / max * 100}%`;
        byId("donation-expenses-bar").style.width = `${spent / max * 100}%`;
        byId("donation-comparison").hidden = false;
      }
    }
    byId("donation-budget-note").textContent = demo
      ? "Diese Beispielbeträge zeigen, wie das offene Budget aussehen wird. Sie sind keine tatsächlichen Spenden oder Betriebskosten."
      : `Bestätigte Beträge · Stand ${new Intl.DateTimeFormat("de-CH", { dateStyle: "medium" }).format(verifiedAt)}. Noch nicht abgerechnete Kosten sind nicht enthalten.`;
  }).catch(() => { /* Keep the honest, accessible unconfigured state. */ });
})();
