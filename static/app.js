const chat = document.getElementById('chat');
const input = document.getElementById('q');
const sendBtn = document.getElementById('send');
const statusEl = document.getElementById('status');
const reindexBtn = document.getElementById('reindex');

const samplesIn = [
  "What are your pricing models?",
  "What is your SLA for a critical outage (Severity 1)?",
  "Can we sign an NDA?",
  "What is included in the Discovery session?",
];

const samplesOut = [
  "What is Bitcoin price today?",
  "Can you draft a legal contract for me?",
  "Where is your office address?",
];

function chip(text) {
  const span = document.createElement('span');
  span.className = 'chip';
  span.textContent = text;
  return span;
}

function addMsg(text, who, metaObj=null) {
  const div = document.createElement('div');
  div.className = 'msg ' + who;
  if (who === 'bot' && typeof mdToHtml === 'function') {
    div.innerHTML = mdToHtml(text);
  } else {
    div.textContent = text;
  }
  chat.appendChild(div);

  if (metaObj) {
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.appendChild(chip(metaObj.mode));
    meta.appendChild(chip(`confidence=${metaObj.conf.toFixed(2)}`));
    if (metaObj.sources && metaObj.sources.length) {
      metaObj.sources.forEach(s => meta.appendChild(chip(s)));
    } else {
      meta.appendChild(chip("no sources"));
    }
    chat.appendChild(meta);
  }

  chat.scrollTop = chat.scrollHeight;
}

async function sendQuestion(q) {
  const question = (q ?? input.value).trim();
  if (!question) return;

  addMsg(question, 'me');
  input.value = '';
  sendBtn.disabled = true;
  statusEl.textContent = "Thinking…";

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ question })
    });

    const data = await res.json();
    const isFallback = !!data.is_fallback;

    addMsg(data.answer, 'bot', {
      conf: data.confidence ?? 0,
      sources: data.sources ?? [],
      mode: isFallback ? "fallback" : "grounded",
    });
  } catch (e) {
    addMsg("Server error. Please try again.", 'bot', {conf: 0, sources: [], mode:"error"});
  } finally {
    sendBtn.disabled = false;
    statusEl.textContent = "Ready";
  }
}

sendBtn.addEventListener('click', () => sendQuestion());
input.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendQuestion(); });

document.querySelector('[data-fill="in"]').addEventListener('click', () => {
  const q = samplesIn[Math.floor(Math.random() * samplesIn.length)];
  sendQuestion(q);
});
document.querySelector('[data-fill="out"]').addEventListener('click', () => {
  const q = samplesOut[Math.floor(Math.random() * samplesOut.length)];
  sendQuestion(q);
});

reindexBtn.addEventListener('click', async () => {
  if (!confirm("Rebuild index from knowledge_base?")) return;
  statusEl.textContent = "Reindexing…";
  try {
    const res = await fetch('/reindex', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      addMsg(`Reindex complete. docs=${data.stats.docs}, chunks=${data.stats.chunks}`, 'bot',
        {conf: 1.0, sources: [], mode:"system"});
    } else {
      addMsg("Reindex failed.", 'bot', {conf: 0, sources: [], mode:"error"});
    }
  } catch (e) {
    addMsg("Reindex failed due to server error.", 'bot', {conf: 0, sources: [], mode:"error"});
  } finally {
    statusEl.textContent = "Ready";
  }
});

addMsg("Hi! Ask me about services, pricing, process, support, or policies. I will answer only from the knowledge base.", 'bot',
  {conf: 1.0, sources: ["knowledge_base"], mode:"system"});
