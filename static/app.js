
const guided = {
  "Services": [
    "What services do you offer?",
    "What is included in the Discovery session?",
    "What do you actually deliver in Discovery?",
    "What deliverables do you provide for an MVP build?",
    "What does Maintenance & Support include?"
  ],
  "Pricing": [
    "What are your pricing models?",
    "What are the payment terms for a Fixed Price project?",
    "How does Time & Materials billing work?",
    "When do you start work for Fixed Price projects?"
  ],
  "Engagement process": [
    "What is your engagement process from start to finish?",
    "Can we sign an NDA?",
    "What happens after the first call — what are the steps?",
    "Do you deliver work in sprints?"
  ],
  "Support & SLA": [
    "What are your support hours?",
    "What support channels do you offer?",
    "What is your SLA for a critical outage (Severity 1)?",
    "Do you offer 24/7 support?"
  ],
  "Policies": [
    "What is your privacy policy?",
    "What is your refund policy for Fixed Price work?",
    "Can meetings be rescheduled?",
    "If work started, how is refund calculated?"
  ]
};

function mountGuide() {
  const topicSel = $("topic");
  const promptSel = $("prompt");
  if (!topicSel || !promptSel) return;

  // topics
  Object.keys(guided).forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    topicSel.appendChild(opt);
  });

  function refreshPrompts() {
    const t = topicSel.value;
    promptSel.innerHTML = "";
    (guided[t] || []).forEach((q) => {
      const opt = document.createElement("option");
      opt.value = q;
      opt.textContent = q;
      promptSel.appendChild(opt);
    });
  }

  topicSel.addEventListener("change", refreshPrompts);
  refreshPrompts();

  const insertBtn = $("insert");
  const askBtn = $("askNow");

  function currentPrompt() {
    const v = (promptSel.value || "").trim();
    return v;
  }

  insertBtn && insertBtn.addEventListener("click", () => {
    const q = currentPrompt();
    if (!q) return;
    $("q").value = q;
    $("q").focus();
  });

  askBtn && askBtn.addEventListener("click", () => {
    const q = currentPrompt();
    if (!q) return;
    ask(q);
  });
}


/* global mdToHtml */
const $ = (id) => document.getElementById(id);

const samples = [
  "What services do you offer?",
  "What is included in the Discovery session?",
  "Is the Discovery session free?",
  "How does Time & Materials billing work?",
  "When do you start work for Fixed Price projects?",
  "Do you deliver work in sprints?",
  "What are your support hours?",
  "What is your SLA for Severity 1?",
  "What is your refund policy for Fixed Price work?",
  "Can meetings be rescheduled?",
  "What is Bitcoin price today?",
  "Can you draft a legal contract for me?"
];

function setStatus(text) {
  $("status").textContent = text;
}

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

function renderMessage({ role, text, meta }) {
  const wrap = el("div", "msg " + role);
  const bubble = el("div", "bubble");
  bubble.innerHTML = mdToHtml(text || "");
  wrap.appendChild(bubble);

  if (meta) {
    const metaRow = el("div", "meta");
    const badge = el("span", "badge " + (meta.mode || "grounded"));
    badge.textContent = (meta.mode || "grounded").toUpperCase();
    metaRow.appendChild(badge);

    const conf = el("span", "");
    conf.textContent = "confidence=" + (meta.confidence ?? 0).toFixed(2);
    metaRow.appendChild(conf);

    if (meta.sources && meta.sources.length) {
      const srcWrap = el("div", "sources");
      meta.sources.forEach((s) => {
        const chip = el("span", "source");
        chip.textContent = s;
        srcWrap.appendChild(chip);
      });
      metaRow.appendChild(srcWrap);
    }
    bubble.appendChild(metaRow);
  }

  $("chat").appendChild(wrap);
  $("chat").scrollTop = $("chat").scrollHeight;
}

async function ask(question) {
  const q = (question || "").trim();
  if (!q) return;

  renderMessage({ role: "user", text: q });
  $("q").value = "";
  setStatus("Thinking…");

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q })
    });

    const data = await res.json();
    const meta = {
      mode: data.mode || (data.is_fallback ? "fallback" : "grounded"),
      confidence: Number(data.confidence || 0),
      sources: data.sources || []
    };
    renderMessage({ role: "bot", text: data.answer || "", meta });
    setStatus("Ready");
  } catch (e) {
    renderMessage({ role: "bot", text: "Server error. Please try again.", meta: { mode: "error", confidence: 0, sources: [] } });
    setStatus("Error");
  }
}

function mountSamples() {
  const wrap = $("samples");
  if (!wrap) return;
  samples.forEach((s) => {
    const c = el("div", "chip");
    c.textContent = s;
    c.addEventListener("click", () => ask(s));
    wrap.appendChild(c);
  });
}

async function reindex() {
  setStatus("Reindexing…");
  try {
    const res = await fetch("/reindex", { method: "POST" });
    const data = await res.json();
    if (data && data.ok) {
      setStatus("Reindexed");
      setTimeout(() => setStatus("Ready"), 1000);
    } else {
      setStatus("Reindex failed");
    }
  } catch (e) {
    setStatus("Reindex failed");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  mountSamples();
  mountGuide();
  renderMessage({
    role: "bot",
    text: "Hi! Ask me anything about ARV Digital Services (services, pricing, process, support/SLA, or policies).\n\nIf something is unclear, I’ll ask a quick clarifying question.",
    meta: { mode: "grounded", confidence: 1.0, sources: [] }
  });

  $("form").addEventListener("submit", (e) => {
    e.preventDefault();
    ask($("q").value);
  });

  $("reindex").addEventListener("click", () => reindex());
});
