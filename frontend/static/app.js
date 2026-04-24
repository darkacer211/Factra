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
    html = html.replace(re, (match) => `<mark>${match}</mark>`);
  });
  return html;
}

function setModeUI(mode) {
  const textBox = document.getElementById("textBox");
  const urlBox = document.getElementById("urlBox");
  if (mode === "url") {
    textBox.classList.add("hidden");
    urlBox.classList.remove("hidden");
  } else {
    urlBox.classList.add("hidden");
    textBox.classList.remove("hidden");
  }
}

function updateGauge(score) {
  const g = document.getElementById("gauge");
  const v = document.getElementById("scoreValue");
  const num = Number(score);
  
  // Animate the number
  let current = 0;
  const step = Math.ceil(num / 30) || 1;
  const interval = setInterval(() => {
    current += step;
    if (current >= num) {
      current = num;
      clearInterval(interval);
    }
    v.textContent = current;
  }, 20);

  // Update CSS variables for visual gauge
  g.style.setProperty("--p", num);
  const color = num > 75 ? "#10b981" : num > 40 ? "#f59e0b" : "#ef4444";
  g.style.setProperty("--c", color);
}

function updateHistorySidebar(newScan = null) {
  const container = document.getElementById("historyItems");
  let history = JSON.parse(localStorage.getItem("fnd_history") || "[]");

  if (newScan) {
    history.unshift(newScan);
    history = history.slice(0, 10); // Keep last 10
    localStorage.setItem("fnd_history", JSON.stringify(history));
  }

  if (history.length === 0) {
    container.innerHTML = `<p class="empty-state">No recent scans</p>`;
    return;
  }

  container.innerHTML = history.map((item, idx) => `
    <div class="history-item" onclick="loadFromHistory(${idx})">
      <div class="title">${escapeHtml(item.text.slice(0, 40))}...</div>
      <div class="meta">${item.prediction} • ${item.score}% • ${item.date}</div>
    </div>
  `).join("");
}

window.loadFromHistory = function(idx) {
  const history = JSON.parse(localStorage.getItem("fnd_history") || "[]");
  const item = history[idx];
  if (!item) return;
  document.getElementById("mode").value = "text";
  setModeUI("text");
  document.getElementById("textInput").value = item.text;
  // Trigger analysis if needed, or just populate
};

function checkHandOff() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("handoff") !== "1") return;

  const data = {
    prediction: params.get("p"),
    credibility_score: params.get("s"),
    confidence: params.get("c"),
    explanation: params.get("e"),
    suspicious_words: params.get("k") ? params.get("k").split(",") : [],
    text: params.get("t"),
    tone: params.get("tone"),
    comp: params.get("comp"),
    obj: params.get("obj"),
    sq: params.get("sq")
  };

  const welcome = document.getElementById("welcomeMessage");
  if (welcome) welcome.classList.add("hidden");

  const report = document.getElementById("resultsContainer");
  if (report) report.classList.remove("hidden");
  document.querySelector(".header h1").textContent = "Factra Analysis Report";

  // Populate results
  updateGauge(data.credibility_score);
  
  const conf = (Number(data.confidence) * 100).toFixed(2);
  const confBar = document.getElementById("confBar");
  const confValue = document.getElementById("confValue");
  if (confBar) confBar.style.width = `${conf}%`;
  if (confValue) confValue.textContent = `${conf}%`;

  const pred = String(data.prediction).toUpperCase();
  const badg = document.getElementById("predBadge");
  if (badg) {
    badg.textContent = pred;
    badg.className = `badge ${pred.toLowerCase()}`;
  }

  const expEl = document.getElementById("explanationText");
  if (expEl) {
    const explanationHtml = highlightWords(data.explanation || "", data.suspicious_words || []);
    expEl.innerHTML = explanationHtml;
  }

  const kList = document.getElementById("keywordsList");
  if (kList) {
    if (data.suspicious_words?.length > 0) {
      kList.innerHTML = data.suspicious_words.map(w => `<span class="keyword-tag">${escapeHtml(w)}</span>`).join("");
    } else {
      kList.innerHTML = `<span class="empty-state">No specific suspicious cues detected.</span>`;
    }
  }

  // Advanced Analysis (safe fallbacks)
  const toneVal = document.getElementById("toneValue");
  if (toneVal) toneVal.textContent = data.tone || "Neutral";
  const compVal = document.getElementById("complexityValue");
  if (compVal) compVal.textContent = data.comp || "Medium";
  const objVal = document.getElementById("objectivityValue");
  if (objVal) objVal.textContent = data.obj || "Objective";

  const factBtn = document.getElementById("factCheckBtn");
  if (factBtn) {
    factBtn.onclick = () => {
      // Use search summary query if available, otherwise fallback to first 12 words of text
      let query = data.sq;
      if (!query && data.text) {
        query = data.text.split(/\s+/).slice(0, 12).join(" ");
      }
      
      const searchUrl = `https://www.google.com/search?q=fact+check+${encodeURIComponent(query || "")}`;
      window.open(searchUrl, "_blank");
    };
  }

  // Save to history
  updateHistorySidebar({
    text: data.text || "Hand-off from extension",
    prediction: data.prediction,
    score: data.credibility_score,
    date: new Date().toLocaleTimeString()
  });
}

document.addEventListener("DOMContentLoaded", () => {
  updateHistorySidebar();
  checkHandOff();
});
