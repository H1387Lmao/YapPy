const pages = [...document.querySelectorAll(".page")];
const navLinks = [...document.querySelectorAll(".nav-link")];
const currentSection = document.getElementById("current-section");
const sidebar = document.getElementById("sidebar");
const scrim = document.getElementById("mobile-scrim");

function navigate() {
  const pageName = location.hash.replace("#", "") || "home";
  const page = document.getElementById(`page-${pageName}`) || document.getElementById("page-home");
  pages.forEach(item => item.classList.toggle("active", item === page));
  navLinks.forEach(link => link.classList.toggle("active", link.dataset.page === page.id.replace("page-", "")));
  currentSection.textContent = page.dataset.title || "Overview";
  sidebar.classList.remove("open");
  scrim.classList.remove("show");
  window.scrollTo({top: 0, behavior: "smooth"});
}
window.addEventListener("hashchange", navigate);
navigate();

document.getElementById("menu-toggle").addEventListener("click", () => {
  sidebar.classList.toggle("open");
  scrim.classList.toggle("show");
});
scrim.addEventListener("click", () => {
  sidebar.classList.remove("open");
  scrim.classList.remove("show");
});

function getCopyText(button) {
  const id = button.dataset.copyId;
  if (id) {
    const el = document.getElementById(id);
    return el ? el.innerText : "";
  }
  if (button.dataset.copy) return button.dataset.copy;
  const code = button.closest(".code-card, .terminal-card, .feature-code")?.querySelector("pre code");
  return code ? code.innerText : "";
}
document.addEventListener("click", async event => {
  const button = event.target.closest(".copy-button");
  if (!button) return;
  const original = button.textContent;
  try {
    await navigator.clipboard.writeText(getCopyText(button));
    button.textContent = "Copied";
  } catch {
    const area = document.createElement("textarea");
    area.value = getCopyText(button);
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
    button.textContent = "Copied";
  }
  setTimeout(() => button.textContent = original, 1200);
});

// Small, dependency-free Python highlighter. Output is escaped before token spans are added.
function highlightPython(source) {
  const tokenPattern = /(#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:async|await|and|as|assert|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|not|or|pass|raise|return|try|while|with|yield|True|False|None)\b|\b(?:print|len|range|str|int|float|list|dict|set|super|open|isinstance|enumerate)\b|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*(?=\s*\())/g;
  let out = "", last = 0, match;
  while ((match = tokenPattern.exec(source))) {
    out += escapeHTML(source.slice(last, match.index));
    const token = match[0];
    let cls = "tok-function";
    if (token.startsWith("#")) cls = "tok-comment";
    else if (/^["']/.test(token)) cls = "tok-string";
    else if (/^(async|await|and|as|assert|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|not|or|pass|raise|return|try|while|with|yield|True|False|None)$/.test(token)) cls = "tok-keyword";
    else if (/^(print|len|range|str|int|float|list|dict|set|super|open|isinstance|enumerate)$/.test(token)) cls = "tok-builtin";
    else if (/^\d/.test(token)) cls = "tok-number";
    out += `<span class="${cls}">${escapeHTML(token)}</span>`;
    last = tokenPattern.lastIndex;
  }
  return out + escapeHTML(source.slice(last));
}
function escapeHTML(value) {
  return value.replace(/[&<>"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[char]));
}
document.querySelectorAll("code.python-code").forEach(code => {
  code.innerHTML = highlightPython(code.textContent);
});

const featureList = document.getElementById("feature-list");
const featureSearch = document.getElementById("feature-search");
const featureCount = document.getElementById("feature-count");
let features = [];

function renderFeatures() {
  const query = featureSearch.value.trim().toLowerCase();
  const filtered = features.filter(item => `${item.title} ${item.desc}`.toLowerCase().includes(query));
  featureCount.textContent = `${filtered.length} feature${filtered.length === 1 ? "" : "s"}`;
  if (!filtered.length) {
    featureList.innerHTML = '<div class="loading">No features match that search.</div>';
    return;
  }
  featureList.innerHTML = filtered.map((item, index) => {
    const title = escapeHTML(item.title || "Untitled feature");
    const desc = escapeHTML(item.desc || "");
    const code = typeof item.code === "string" && item.code.trim()
      ? `<div class="feature-code"><div class="code-head"><span>Python</span><button class="copy-button" data-copy-id="feature-code-${index}">Copy</button></div><pre><code id="feature-code-${index}">${highlightPython(item.code)}</code></pre></div>` : "";
    const img = item.image ? `<img class="feature-image" src="${escapeHTML(item.image)}" alt="${escapeHTML(item.imageAlt || item.title || "Feature image")}" loading="lazy">` : "";
    let action = "";
    if (item.button && item.button.label) {
      if (item.button.type === "link" && isSafeURL(item.button.href)) {
        action = `<a class="feature-action" href="${escapeHTML(item.button.href)}" target="_blank" rel="noreferrer">${escapeHTML(item.button.label)} ↗</a>`;
      } else if (item.button.type === "action" && ["copy-install", "show-note"].includes(item.button.action)) {
        action = `<button class="feature-action" data-feature-action="${escapeHTML(item.button.action)}" data-action-value="${escapeHTML(item.button.value || "")}" data-action-note="${escapeHTML(item.button.note || "")}">${escapeHTML(item.button.label)} →</button>`;
      }
    }
    return `<article class="feature-item"><div class="feature-item-top"><div><h3>${title}</h3><p>${desc}</p></div><span class="feature-badge">FEATURE</span></div>${img}${code}${action}</article>`;
  }).join("");
}
function isSafeURL(url) {
  try { const parsed = new URL(url, location.href); return ["https:", "http:"].includes(parsed.protocol); }
  catch { return false; }
}
featureSearch.addEventListener("input", renderFeatures);
featureList.addEventListener("click", async event => {
  const button = event.target.closest("[data-feature-action]");
  if (!button) return;
  if (button.dataset.featureAction === "copy-install") {
    try {
      await navigator.clipboard.writeText(button.dataset.actionValue || "python -m pip install python-yappy");
      button.textContent = "Copied";
    } catch { button.textContent = "Copy unavailable"; }
  } else if (button.dataset.featureAction === "show-note") {
    button.textContent = button.dataset.actionNote || "See the repository for details";
  }
});
fetch("features.json")
  .then(response => {
    if (!response.ok) throw new Error("Could not load features.json");
    return response.json();
  })
  .then(data => {
    features = Array.isArray(data.features) ? data.features : [];
    renderFeatures();
  })
  .catch(() => {
    featureList.innerHTML = '<div class="callout"><span class="callout-icon">!</span><p><strong>Feature catalog unavailable</strong><br>Run this website from a local web server so the browser can load <code>features.json</code>. See README.md for options.</p></div>';
  });
