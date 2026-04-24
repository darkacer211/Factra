function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function highlightWords(explanation, suspiciousWords) {
  if (!Array.isArray(suspiciousWords) || suspiciousWords.length === 0) return escapeHtml(explanation);
  let html = escapeHtml(explanation);
  suspiciousWords.forEach((w) => {
    if (!w) return;
    const escaped = w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(escaped, "gi");
    html = html.replace(re, (m) => `<mark>${m}</mark>`);
  });
  return html;
}

async function getApiBase() {
  const { apiBase } = await chrome.storage.sync.get({ apiBase: "http://127.0.0.1:5000" });
  return apiBase;
}

async function setApiBase(v) {
  await chrome.storage.sync.set({ apiBase: v });
}

function setStatus(msg) {
  document.getElementById("status").textContent = msg || "";
}

let lastResult = null;

function setResult(data) {
  lastResult = data;
  const result = document.getElementById("result");
  if (!data) {
    result.classList.add("hidden");
    result.innerHTML = "";
    return;
  }
  const suspicious = data.suspicious_words || [];
  const expl = highlightWords(data.explanation || "", suspicious);
  const pred = String(data.prediction || "");
  const predClass = pred.toLowerCase() === "fake" ? "fake" : "real";
  result.innerHTML = `
    <div class="headline ${predClass}">${escapeHtml(pred)}</div>
    <div class="kv"><strong>Confidence</strong><span>${(Number(data.confidence) * 100).toFixed(2)}%</span></div>
    <div class="kv"><strong>Credibility</strong><span>${escapeHtml(String(data.credibility_score))} / 100</span></div>
    <div style="margin-top:10px;"><strong>Explanation:</strong> ${expl}</div>
  `;
  result.classList.remove("hidden");
}

async function apiPost(path, body) {
  const base = await getApiBase();
  const url = `${base}${path}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || `Request failed (${resp.status})`);
  return data;
}

async function extractPageText() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active tab found.");
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      const ps = Array.from(document.querySelectorAll("p"));
      const chunks = ps
        .map((p) => (p.innerText || "").trim())
        .filter(Boolean)
        .slice(0, 250);
      let text = chunks.join("\n");
      // Keep payload size reasonable.
      if (text.length > 8000) text = text.slice(0, 8000);
      return { text, url: location.href };
    },
  });
  return result;
}

async function applyHighlightsToPage(words) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active tab found.");

  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    args: [Array.isArray(words) ? words : []],
    func: (ws) => {
      const ATTR = "data-fnd-mark";
      const STYLE_ID = "fnd-style";

      const escapeRegExp = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

      // Clear old highlights
      const clear = () => {
        document.querySelectorAll(`mark[${ATTR}]`).forEach((m) => {
          const parent = m.parentNode;
          if (!parent) return;
          parent.replaceChild(document.createTextNode(m.textContent || ""), m);
          parent.normalize();
        });
      };

      clear();

      if (!ws || ws.length === 0) return;

      // Add style once
      if (!document.getElementById(STYLE_ID)) {
        const st = document.createElement("style");
        st.id = STYLE_ID;
        st.textContent = `
          mark[${ATTR}] {
            background: #ffdd57;
            color: #0b1220;
            padding: 0 3px;
            border-radius: 4px;
          }
        `;
        document.documentElement.appendChild(st);
      }

      const cleaned = Array.from(new Set(ws.map((w) => String(w).trim()).filter(Boolean))).slice(0, 25);
      if (cleaned.length === 0) return;

      const re = new RegExp(`\\b(${cleaned.map(escapeRegExp).join("|")})\\b`, "gi");

      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
          const p = node.parentElement;
          if (!p) return NodeFilter.FILTER_REJECT;
          if (p.closest("script,style,noscript,textarea,input,code,pre")) return NodeFilter.FILTER_REJECT;
          if (!node.nodeValue || node.nodeValue.trim().length === 0) return NodeFilter.FILTER_REJECT;
          if (!re.test(node.nodeValue)) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        },
      });

      const nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);

      for (const n of nodes) {
        const text = n.nodeValue;
        if (!text) continue;
        const parts = text.split(re);
        if (parts.length <= 1) continue;
        const frag = document.createDocumentFragment();
        for (let i = 0; i < parts.length; i++) {
          const part = parts[i];
          if (!part) continue;
          if (i % 2 === 1) {
            const m = document.createElement("mark");
            m.setAttribute(ATTR, "1");
            m.textContent = part;
            frag.appendChild(m);
          } else {
            frag.appendChild(document.createTextNode(part));
          }
        }
        n.parentNode.replaceChild(frag, n);
      }
    },
  });
}

async function clearHighlightsOnPage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active tab found.");
  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      const ATTR = "data-fnd-mark";
      document.querySelectorAll(`mark[${ATTR}]`).forEach((m) => {
        const parent = m.parentNode;
        if (!parent) return;
        parent.replaceChild(document.createTextNode(m.textContent || ""), m);
        parent.normalize();
      });
    },
  });
}

async function onAnalyzeTab() {
  setResult(null);
  setStatus("Analyzing this page...");
  try {
    const extracted = await extractPageText();
    if (!extracted?.text || extracted.text.trim().length < 80) {
      // Fallback to server-side URL scraping if page extraction is too small.
      setStatus("Low text found; trying URL scraping...");
      const data = await apiPost("/predict_url", { url: extracted?.url || "" });
      data.originalText = "Website content from: " + (extracted?.url || "current tab");
      setResult(data);
      await applyHighlightsToPage(data.suspicious_words || []);
      setStatus("");
      return;
    }
    const data = await apiPost("/predict", { text: extracted.text });
    data.originalText = extracted.text;
    setResult(data);
    await applyHighlightsToPage(data.suspicious_words || []);
    setStatus("");
  } catch (e) {
    setStatus(`Error: ${e.message}`);
  }
}

async function onSaveApi() {
  const v = (document.getElementById("apiBase").value || "").trim();
  if (!v) return;
  await setApiBase(v.replace(/\/+$/, ""));
  setStatus("Saved API URL.");
  setTimeout(() => setStatus(""), 1200);
}

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("apiBase").value = await getApiBase();
  document.getElementById("saveApi").addEventListener("click", onSaveApi);
  document.getElementById("analyzeTab").addEventListener("click", onAnalyzeTab);
  document.getElementById("openDashboard").addEventListener("click", async () => {
    const base = await getApiBase();
    let url = base;
    if (lastResult) {
      const params = new URLSearchParams({
        handoff: "1",
        p: lastResult.prediction || "",
        s: lastResult.credibility_score || "",
        c: lastResult.confidence || "",
        e: lastResult.explanation || "",
        k: (lastResult.suspicious_words || []).join(","),
        t: (lastResult.originalText || "").slice(0, 1000), // Pass snippet
        sq: lastResult.search_query || ""
      });
      url += "/?" + params.toString();
    }
    chrome.tabs.create({ url: url });
  });
  document.getElementById("clearHighlights").addEventListener("click", async () => {
    setStatus("Clearing highlights...");
    try {
      await clearHighlightsOnPage();
      setStatus("");
    } catch (e) {
      setStatus(`Error: ${e.message}`);
    }
  });
});

