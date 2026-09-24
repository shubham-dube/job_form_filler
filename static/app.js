// FormFiller AI - Interactive Client-Side Controller

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  fetchHealthStatus();
  fetchProfile();
  fetchHistory();
  setupBookmarklet();
});

// Navigation Handling
function initNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const pageTitle = document.getElementById("page-title");
  const pageSubtitle = document.getElementById("page-subtitle");

  const tabTitles = {
    "filler-tab": {
      title: "Auto-Fill Google Form",
      subtitle: "Map your master profile & targeted job description directly into Google Form fields."
    },
    "profile-tab": {
      title: "Master Profile Studio",
      subtitle: "Manage your single source of truth for resume details, CTC, notice period, and project stories."
    },
    "extension-tab": {
      title: "Chrome Extension (Manifest V3)",
      subtitle: "Zero-effort 1-click auto-fill directly in your signed-in browser tab."
    },
    "bookmarklet-tab": {
      title: "Universal Mobile Bookmarklet",
      subtitle: "Pre-fill forms from your iPhone (Safari) or Android (Chrome) without extensions."
    },
    "history-tab": {
      title: "Application History",
      subtitle: "Audit log of all AI pre-filled Google Forms."
    }
  };

  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");

      navItems.forEach(n => n.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      item.classList.add("active");
      const targetPane = document.getElementById(tabId);
      if (targetPane) targetPane.classList.add("active");

      if (tabTitles[tabId]) {
        pageTitle.textContent = tabTitles[tabId].title;
        pageSubtitle.textContent = tabTitles[tabId].subtitle;
      }

      if (tabId === "history-tab") {
        fetchHistory();
      }
    });
  });

  const btnQuickNew = document.getElementById("btn-quick-new");
  if (btnQuickNew) {
    btnQuickNew.addEventListener("click", () => {
      document.getElementById("nav-filler").click();
      document.getElementById("form-url").value = "";
      document.getElementById("job-description").value = "";
      document.getElementById("custom-notes").value = "";
      document.getElementById("results-card").classList.add("hidden");
    });
  }
}

// System Health Status
async function fetchHealthStatus() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();

    document.getElementById("model-name").textContent = data.gemini_model || "Gemini Flash";
    const statusLabel = document.getElementById("status-label");
    const statusDot = document.querySelector(".status-dot");

    statusLabel.textContent = "API Connected";
    statusDot.classList.remove("offline");
    statusDot.classList.add("online");

    const profileStatus = document.getElementById("profile-status");
    if (data.profile_configured) {
      profileStatus.textContent = `Profile (${data.profile_character_count} chars)`;
    } else {
      profileStatus.textContent = "Profile Needs Setup";
      profileStatus.style.color = "var(--accent-amber)";
    }
  } catch (err) {
    document.getElementById("status-label").textContent = "API Offline";
    const statusDot = document.querySelector(".status-dot");
    statusDot.classList.remove("online");
    statusDot.classList.add("offline");
  }
}

// Source Mode Switching
function switchSourceMode(mode) {
  const toggleUrl = document.getElementById("toggle-url");
  const toggleHtml = document.getElementById("toggle-html");
  const urlGroup = document.getElementById("url-group");
  const htmlGroup = document.getElementById("html-group");

  if (mode === "url") {
    toggleUrl.classList.add("active");
    toggleHtml.classList.remove("active");
    urlGroup.classList.remove("hidden");
    htmlGroup.classList.add("hidden");
  } else {
    toggleHtml.classList.add("active");
    toggleUrl.classList.remove("active");
    htmlGroup.classList.remove("hidden");
    urlGroup.classList.add("hidden");
  }
}

// Clipboard Paste Helper
async function pasteFromClipboard(targetId) {
  try {
    const text = await navigator.clipboard.readText();
    const target = document.getElementById(targetId);
    if (target) {
      target.value = text;
      showToast("Pasted from clipboard!", "success");
    }
  } catch (err) {
    showToast("Clipboard permission denied. Please paste manually.", "error");
  }
}

// Form Filling Execution
async function executeFormFill() {
  const isUrlMode = document.getElementById("toggle-url").classList.contains("active");
  const formUrl = document.getElementById("form-url").value.trim();
  const formHtml = document.getElementById("form-html").value.trim();
  const jd = document.getElementById("job-description").value.trim();
  const notes = document.getElementById("custom-notes").value.trim();

  if (isUrlMode && !formUrl) {
    showToast("Please enter a Google Form URL.", "error");
    return;
  }
  if (!isUrlMode && !formHtml) {
    showToast("Please paste HTML or FB_PUBLIC_LOAD_DATA_.", "error");
    return;
  }

  // UI Loading State
  const loadingState = document.getElementById("loading-state");
  const resultsCard = document.getElementById("results-card");
  const btnFill = document.getElementById("btn-generate-prefill");

  loadingState.classList.remove("hidden");
  resultsCard.classList.add("hidden");
  btnFill.disabled = true;

  const payload = {
    url: formUrl || undefined,
    job_description: jd || undefined,
    notes: notes || undefined
  };

  if (!isUrlMode) {
    // Check if user pasted pure JSON/array vs raw HTML
    if (formHtml.startsWith("[") && formHtml.endsWith("]")) {
      try {
        payload.fb_data = JSON.parse(formHtml);
      } catch (e) {
        payload.html = formHtml;
      }
    } else {
      payload.html = formHtml;
    }
  }

  try {
    const response = await fetch("/api/fill", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
      if (response.status === 401 && data.error === "google_sign_in_required") {
        showToast("Form requires Google sign-in. Use the Chrome Extension or Bookmarklet!", "error", 6000);
      } else {
        showToast(data.detail || data.message || "Failed to process form.", "error");
      }
      return;
    }

    renderResults(data);
    showToast("Pre-filled link generated successfully!", "success");
    fetchHistory();
  } catch (err) {
    showToast(`Network error: ${err.message}`, "error");
  } finally {
    loadingState.classList.add("hidden");
    btnFill.disabled = false;
  }
}

// Dry Run Inspection
async function executeDryRun() {
  const isUrlMode = document.getElementById("toggle-url").classList.contains("active");
  const formUrl = document.getElementById("form-url").value.trim();
  const formHtml = document.getElementById("form-html").value.trim();

  if (isUrlMode && !formUrl) {
    showToast("Please enter a Google Form URL.", "error");
    return;
  }
  if (!isUrlMode && !formHtml) {
    showToast("Please paste HTML or form data.", "error");
    return;
  }

  const payload = {
    url: formUrl || undefined,
    html: !isUrlMode ? formHtml : undefined
  };

  try {
    showToast("Inspecting form questions...", "info");
    const response = await fetch("/api/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json();

    if (!response.ok) {
      showToast(data.detail || data.message || "Failed to parse form.", "error");
      return;
    }

    alert(`Form Title: ${data.title}\nTotal Questions: ${data.stats.total}\nFillable: ${data.stats.fillable}\nFile Uploads: ${data.stats.file_uploads}`);
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  }
}

// Render Results View
function renderResults(data) {
  const resultsCard = document.getElementById("results-card");
  resultsCard.classList.remove("hidden");
  resultsCard.scrollIntoView({ behavior: "smooth" });

  document.getElementById("result-form-title").textContent = data.title;
  document.getElementById("result-form-desc").textContent = data.description || "No description";
  document.getElementById("result-url-text").textContent = data.prefilled_url;
  document.getElementById("btn-open-form").href = data.prefilled_url;

  // Stats badges
  const statsContainer = document.getElementById("stats-badges");
  statsContainer.innerHTML = `
    <div class="stat-pill">Total: <strong>${data.stats.total}</strong></div>
    <div class="stat-pill">Fillable: <strong>${data.stats.fillable}</strong></div>
  `;

  // File Upload warning
  const fileUploadAlert = document.getElementById("file-upload-alert");
  if (data.file_upload_questions && data.file_upload_questions.length > 0) {
    fileUploadAlert.classList.remove("hidden");
    document.getElementById("file-upload-text").textContent =
      `Google Form requires manual file attachment for: ${data.file_upload_questions.join(", ")}. All text answers are pre-filled; just attach your resume and hit submit!`;
  } else {
    fileUploadAlert.classList.add("hidden");
  }

  // Populate Table
  const tableBody = document.getElementById("answers-table-body");
  tableBody.innerHTML = "";

  data.answers.forEach((ans, idx) => {
    const tr = document.createElement("tr");

    let ansDisplay = Array.isArray(ans.answer) ? ans.answer.join(", ") : ans.answer;
    let otherTag = ans.is_other ? `<span class="ans-other-tag">Other</span> ` : "";

    let confClass = "conf-high";
    if (ans.confidence.toUpperCase() === "MEDIUM") confClass = "conf-medium";
    if (ans.confidence.toUpperCase() === "LOW") confClass = "conf-low";

    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td><strong>${escapeHtml(ans.question_title)}</strong></td>
      <td><span class="ans-text">${otherTag}${escapeHtml(ansDisplay)}</span></td>
      <td style="text-align: center;"><span class="legend-badge ${confClass}">${ans.confidence.toUpperCase()}</span></td>
      <td><span class="reasoning-text">${escapeHtml(ans.reasoning || "-")}</span></td>
    `;
    tableBody.appendChild(tr);
  });
}

function copyPrefillUrl() {
  const url = document.getElementById("result-url-text").textContent;
  if (url) {
    navigator.clipboard.writeText(url);
    showToast("Pre-filled URL copied to clipboard!", "success");
  }
}

// Master Profile Management
async function fetchProfile() {
  try {
    const res = await fetch("/api/profile");
    if (!res.ok) throw new Error("Failed to load profile");
    const data = await res.json();
    document.getElementById("profile-textarea").value = data.content || "";
  } catch (err) {
    console.error("Profile load error:", err);
  }
}

async function saveProfile() {
  const content = document.getElementById("profile-textarea").value;
  const statusEl = document.getElementById("profile-save-status");
  statusEl.textContent = "Saving...";

  try {
    const res = await fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    });
    if (!res.ok) throw new Error("Save failed");
    statusEl.textContent = "All changes saved!";
    showToast("Master Profile saved successfully!", "success");
    fetchHealthStatus();
  } catch (err) {
    statusEl.textContent = "Failed to save";
    showToast(`Failed to save profile: ${err.message}`, "error");
  }
}

// Bookmarklet Setup
function setupBookmarklet() {
  const origin = window.location.origin;
  // Bookmarklet extracts window.FB_PUBLIC_LOAD_DATA_ from active tab and sends it to the web app
  const rawCode = `
    (function(){
      try {
        var data = window.FB_PUBLIC_LOAD_DATA_;
        if (!data) {
          alert('No Google Form detected on this page! Make sure you are viewing a Google Form.');
          return;
        }
        var formUrl = window.location.href;
        var jd = prompt('FormFiller AI\\n\\nEnter Job Description (or leave blank to use Master Profile):', '');
        if (jd === null) return;
        
        var payload = {
          url: formUrl,
          fb_data: data,
          job_description: jd || ''
        };
        
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = '${origin}/api/fill';
        form.target = '_blank';
        
        var input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'payload';
        input.value = JSON.stringify(payload);
        form.appendChild(input);
        
        document.body.appendChild(form);
        
        // Use Fetch with visual alert
        var banner = document.createElement('div');
        banner.style.cssText = 'position:fixed;top:20px;right:20px;z-index:999999;background:#181824;color:#fff;padding:16px 24px;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.7);font-family:sans-serif;font-size:14px;border:1px solid #6366f1;';
        banner.innerHTML = '⚡ FormFiller AI is synthesizing answers with Gemini...';
        document.body.appendChild(banner);
        
        fetch('${origin}/api/fill', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        })
        .then(function(r){ return r.json(); })
        .then(function(res){
          banner.remove();
          if (res.prefilled_url) {
            window.location.href = res.prefilled_url;
          } else {
            alert('Form prefill error: ' + (res.detail || JSON.stringify(res)));
          }
        })
        .catch(function(e){
          banner.remove();
          alert('FormFiller AI Connection Error: Make sure your server at ${origin} is running.');
        });
      } catch(err) {
        alert('Error: ' + err.message);
      }
    })();
  `.replace(/\s+/g, " ").trim();

  const bookmarkletHref = `javascript:${encodeURIComponent(rawCode)}`;
  const linkEl = document.getElementById("bookmarklet-link");
  if (linkEl) {
    linkEl.setAttribute("href", bookmarkletHref);
  }
}

function copyBookmarkletCode() {
  const linkEl = document.getElementById("bookmarklet-link");
  if (linkEl) {
    navigator.clipboard.writeText(linkEl.getAttribute("href"));
    showToast("Bookmarklet code copied! Follow the mobile instructions below.", "success", 4000);
  }
}

// Application History
async function fetchHistory() {
  try {
    const res = await fetch("/api/history");
    if (!res.ok) return;
    const data = await res.json();
    const tbody = document.getElementById("history-table-body");
    if (!tbody) return;

    tbody.innerHTML = "";
    if (!data.history || data.history.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">No applications generated yet.</td></tr>`;
      return;
    }

    data.history.forEach(item => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="color: var(--text-muted);">${item.timestamp}</td>
        <td><strong>${escapeHtml(item.title)}</strong></td>
        <td>${item.questions_count} questions</td>
        <td style="font-size: 0.8rem; color: var(--text-secondary); max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(item.job_description_snippet || "-")}</td>
        <td>${item.has_file_upload ? '<span class="optional-badge" style="color: var(--accent-amber);">Upload Resume</span>' : '<span style="color: var(--text-muted);">None</span>'}</td>
        <td style="text-align: right;">
          <a href="${item.prefilled_url}" target="_blank" class="btn btn-secondary btn-sm">Open Form</a>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Failed to fetch history:", err);
  }
}

async function clearHistory() {
  if (!confirm("Are you sure you want to clear your application history?")) return;
  try {
    await fetch("/api/history", { method: "DELETE" });
    fetchHistory();
    showToast("History cleared", "info");
  } catch (err) {
    showToast("Failed to clear history", "error");
  }
}

// Toast Notifications
function showToast(message, type = "info", duration = 3000) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  const icon = type === "success" ? "✓" : type === "error" ? "✕" : "ℹ";
  toast.innerHTML = `<span><strong>${icon}</strong></span><span>${escapeHtml(message)}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
