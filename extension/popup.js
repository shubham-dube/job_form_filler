// FormFiller AI - Extension Popup Controller

let currentFormData = null;
let currentPrefilledUrl = null;
let activeTabId = null;
let serverUrl = "https://job-form-filler.onrender.com";

document.addEventListener("DOMContentLoaded", async () => {
  // Load settings
  const config = await chrome.storage.sync.get({
    serverUrl: "https://job-form-filler.onrender.com"
  });
  serverUrl = config.serverUrl.replace(/\/+$/, "");

  // Update Footer Links
  const linkDash = document.getElementById("link-dashboard");
  if (linkDash) linkDash.href = `${serverUrl}/dashboard`;

  const btnOpenDash = document.getElementById("btn-open-dashboard");
  if (btnOpenDash) {
    btnOpenDash.addEventListener("click", () => {
      chrome.tabs.create({ url: `${serverUrl}/dashboard` });
    });
  }

  // Check backend server status
  checkServerHealth();

  // Inspect Active Tab
  initActiveTab();

  // Attach button events
  document.getElementById("btn-paste-jd").addEventListener("click", pasteJdFromClipboard);
  document.getElementById("btn-run-fill").addEventListener("click", runAiAutoFill);
  document.getElementById("btn-ext-copy").addEventListener("click", copyPrefilledUrl);
  document.getElementById("btn-ext-open").addEventListener("click", openPrefilledUrl);
});

async function checkServerHealth() {
  const statusLabel = document.getElementById("ext-server-status");
  const dot = document.querySelector(".status-dot");
  try {
    const res = await fetch(`${serverUrl}/api/health`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    statusLabel.textContent = `API: Online (${data.gemini_model})`;
    dot.className = "status-dot online";
  } catch (e) {
    statusLabel.textContent = "API: Offline (Start server)";
    dot.className = "status-dot offline";
  }
}

async function initActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) return;
  activeTabId = tab.id;

  const isGoogleFormUrl = tab.url && (tab.url.includes("docs.google.com/forms") || tab.url.includes("forms.gle"));

  if (!isGoogleFormUrl) {
    showNoFormView();
    return;
  }

  // Ask content script for form metadata & FB_PUBLIC_LOAD_DATA_
  try {
    chrome.tabs.sendMessage(tab.id, { action: "GET_FORM_DATA" }, (response) => {
      if (chrome.runtime.lastError || !response) {
        // Content script might not have loaded or tab is restricted
        document.getElementById("ext-form-title").textContent = tab.title || "Google Form";
        currentFormData = { url: tab.url };
        showFormDetectedView();
      } else {
        currentFormData = response;
        document.getElementById("ext-form-title").textContent = response.title || tab.title || "Google Form";
        showFormDetectedView();
      }
    });
  } catch (err) {
    document.getElementById("ext-form-title").textContent = tab.title || "Google Form";
    currentFormData = { url: tab.url };
    showFormDetectedView();
  }
}

function showFormDetectedView() {
  document.getElementById("form-detected-view").classList.remove("hidden");
  document.getElementById("no-form-view").classList.add("hidden");
}

function showNoFormView() {
  document.getElementById("form-detected-view").classList.add("hidden");
  document.getElementById("no-form-view").classList.remove("hidden");
}

async function pasteJdFromClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      document.getElementById("ext-jd").value = text;
    }
  } catch (err) {
    console.warn("Could not read clipboard:", err);
  }
}

async function runAiAutoFill() {
  const btn = document.getElementById("btn-run-fill");
  const loading = document.getElementById("ext-loading");
  const results = document.getElementById("ext-results");
  const loadingMsg = document.getElementById("loading-msg");

  const jd = document.getElementById("ext-jd").value.trim();
  const notes = document.getElementById("ext-notes").value.trim();

  btn.disabled = true;
  loading.classList.remove("hidden");
  results.classList.add("hidden");
  loadingMsg.textContent = "Synthesizing answers with Gemini...";

  const payload = {
    url: currentFormData ? currentFormData.url : undefined,
    fb_data: currentFormData ? currentFormData.fb_data : undefined,
    html: currentFormData && !currentFormData.fb_data ? currentFormData.html_fallback : undefined,
    job_description: jd || undefined,
    notes: notes || undefined
  };

  try {
    const res = await fetch(`${serverUrl}/api/fill`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.message || "Failed to generate prefill.");
    }

    currentPrefilledUrl = data.prefilled_url;
    renderResults(data);
  } catch (err) {
    alert(`Auto-Fill Error: ${err.message}\nMake sure your server is running at ${serverUrl}`);
  } finally {
    btn.disabled = false;
    loading.classList.add("hidden");
  }
}

function renderResults(data) {
  const results = document.getElementById("ext-results");
  results.classList.remove("hidden");

  document.getElementById("ext-stats").textContent =
    `Mapped ${data.stats.fillable} questions (${data.stats.file_uploads ? data.stats.file_uploads + " file upload" : "all auto-filled"})`;

  const previewList = document.getElementById("ext-preview-list");
  previewList.innerHTML = "";

  (data.answers || []).forEach(ans => {
    const item = document.createElement("div");
    item.className = "preview-item";

    const qSpan = document.createElement("span");
    qSpan.className = "preview-q";
    qSpan.textContent = ans.question_title;

    const confSpan = document.createElement("span");
    const conf = (ans.confidence || "HIGH").toUpperCase();
    confSpan.className = `badge-conf ${conf}`;
    confSpan.textContent = conf;

    item.appendChild(qSpan);
    item.appendChild(confSpan);
    previewList.appendChild(item);
  });
}

function copyPrefilledUrl() {
  if (currentPrefilledUrl) {
    navigator.clipboard.writeText(currentPrefilledUrl);
    const btn = document.getElementById("btn-ext-copy");
    const oldText = btn.textContent;
    btn.textContent = "✓ Copied!";
    setTimeout(() => { btn.textContent = oldText; }, 2000);
  }
}

function openPrefilledUrl() {
  if (currentPrefilledUrl && activeTabId) {
    chrome.tabs.update(activeTabId, { url: currentPrefilledUrl });
    window.close(); // Close popup
  }
}
