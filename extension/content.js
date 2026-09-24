// FormFiller AI - Content Script (Runs in Google Forms tabs)

(function () {
  console.log("[FormFiller AI] Content script active on Google Form.");

  // Helper to extract FB_PUBLIC_LOAD_DATA_ from DOM script elements
  function extractFbData() {
    const scripts = document.querySelectorAll("script");
    for (const script of scripts) {
      const text = script.textContent || "";
      if (text.includes("FB_PUBLIC_LOAD_DATA_")) {
        const match = text.match(/FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\])\s*;/s);
        if (match && match[1]) {
          try {
            return JSON.parse(match[1]);
          } catch (e) {
            console.warn("[FormFiller AI] Failed to parse FB_PUBLIC_LOAD_DATA_ JSON:", e);
          }
        }
      }
    }
    return null;
  }

  // Get Form Title from DOM
  function getFormTitle() {
    const titleEl = document.querySelector('[role="heading"][aria-level="1"]') || document.querySelector(".F9fKVc") || document.querySelector("h1");
    if (titleEl && titleEl.textContent) {
      return titleEl.textContent.trim();
    }
    return document.title.replace(" - Google Forms", "").trim() || "Google Form";
  }

  // Inject Floating Button
  function injectFloatingWidget() {
    if (document.getElementById("formfiller-floating-btn")) return;

    const btn = document.createElement("div");
    btn.id = "formfiller-floating-btn";
    btn.innerHTML = `<span class="btn-sparkle">✨</span> <span>Auto-Fill with AI</span>`;
    btn.title = "FormFiller AI: 1-Click Fill with Gemini";
    document.body.appendChild(btn);

    btn.addEventListener("click", () => {
      openModal();
    });
  }

  // Inject Modal Overlay
  function injectModal() {
    if (document.getElementById("formfiller-modal-overlay")) return;

    const overlay = document.createElement("div");
    overlay.id = "formfiller-modal-overlay";
    overlay.innerHTML = `
      <div class="formfiller-modal-card">
        <div class="ff-modal-header">
          <h3><span>✨</span> FormFiller AI</h3>
          <button class="ff-modal-close" id="ff-modal-close-btn">&times;</button>
        </div>
        <div class="ff-modal-body">
          <label for="ff-in-jd">Job Description (JD) <span style="font-weight: normal; color: #9ca3af;">(Recommended)</span></label>
          <textarea id="ff-in-jd" rows="4" placeholder="Paste job description or requirements here to tailor answers..."></textarea>

          <label for="ff-in-notes">Custom Instructions / Notes <span style="font-weight: normal; color: #9ca3af;">(Optional)</span></label>
          <textarea id="ff-in-notes" rows="2" placeholder="E.g., Notice period is negotiable to 15 days..."></textarea>

          <div id="ff-status-msg" style="display: none; font-size: 13px; color: #a5b4fc; margin-bottom: 12px;"></div>

          <div class="ff-modal-footer">
            <button class="ff-btn ff-btn-secondary" id="ff-btn-cancel">Cancel</button>
            <button class="ff-btn ff-btn-primary" id="ff-btn-fill">
              <span>🚀</span> Auto-Fill Form
            </button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    document.getElementById("ff-modal-close-btn").addEventListener("click", closeModal);
    document.getElementById("ff-btn-cancel").addEventListener("click", closeModal);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal();
    });

    document.getElementById("ff-btn-fill").addEventListener("click", handleModalFill);
  }

  function openModal() {
    injectModal();
    const overlay = document.getElementById("formfiller-modal-overlay");
    if (overlay) overlay.classList.add("active");
  }

  function closeModal() {
    const overlay = document.getElementById("formfiller-modal-overlay");
    if (overlay) overlay.classList.remove("active");
  }

  async function handleModalFill() {
    const jd = document.getElementById("ff-in-jd").value.trim();
    const notes = document.getElementById("ff-in-notes").value.trim();
    const btn = document.getElementById("ff-btn-fill");
    const statusMsg = document.getElementById("ff-status-msg");

    btn.disabled = true;
    btn.innerHTML = `<span class="ff-spinner"></span> Synthesizing with Gemini...`;
    statusMsg.style.display = "block";
    statusMsg.textContent = "Connecting to FormFiller AI service...";

    const fbData = extractFbData();
    const url = window.location.href;

    // Get server URL from chrome storage (default http://localhost:8000)
    chrome.storage.sync.get({ serverUrl: "http://localhost:8000" }, async (items) => {
      const serverUrl = items.serverUrl.replace(/\/+$/, "");

      try {
        statusMsg.textContent = "AI is mapping your profile to questions...";
        const res = await fetch(`${serverUrl}/api/fill`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: url,
            fb_data: fbData,
            html: fbData ? undefined : document.documentElement.outerHTML,
            job_description: jd || undefined,
            notes: notes || undefined
          })
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || data.message || "Failed to generate pre-fill.");
        }

        statusMsg.textContent = "Success! Redirecting to pre-filled form...";
        setTimeout(() => {
          window.location.href = data.prefilled_url;
        }, 500);
      } catch (err) {
        statusMsg.style.color = "#f43f5e";
        statusMsg.textContent = `Error: ${err.message}. Ensure your server is running at ${serverUrl}.`;
        btn.disabled = false;
        btn.innerHTML = `<span>🚀</span> Auto-Fill Form`;
      }
    });
  }

  // Listen for messages from popup.js
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "GET_FORM_DATA") {
      const fbData = extractFbData();
      sendResponse({
        url: window.location.href,
        title: getFormTitle(),
        fb_data: fbData,
        has_fb_data: !!fbData,
        html_fallback: fbData ? null : document.documentElement.outerHTML
      });
      return true;
    }
  });

  // Inject on load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", injectFloatingWidget);
  } else {
    injectFloatingWidget();
  }
})();
