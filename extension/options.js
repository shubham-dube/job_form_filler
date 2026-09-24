// FormFiller AI - Options Controller

document.addEventListener("DOMContentLoaded", async () => {
  const config = await chrome.storage.sync.get({
    serverUrl: "http://localhost:8000"
  });
  document.getElementById("server-url").value = config.serverUrl;

  document.getElementById("btn-save").addEventListener("click", saveOptions);
  document.getElementById("btn-test").addEventListener("click", testConnection);
});

async function saveOptions() {
  const serverUrl = document.getElementById("server-url").value.trim().replace(/\/+$/, "");
  const statusMsg = document.getElementById("status-msg");

  await chrome.storage.sync.set({ serverUrl });
  statusMsg.style.color = "#10b981";
  statusMsg.textContent = "Saved!";
  setTimeout(() => { statusMsg.textContent = ""; }, 2500);
}

async function testConnection() {
  const serverUrl = document.getElementById("server-url").value.trim().replace(/\/+$/, "");
  const statusMsg = document.getElementById("status-msg");
  statusMsg.style.color = "#a5b4fc";
  statusMsg.textContent = "Testing...";

  try {
    const res = await fetch(`${serverUrl}/api/health`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    statusMsg.style.color = "#10b981";
    statusMsg.textContent = `Online! (${data.gemini_model})`;
  } catch (err) {
    statusMsg.style.color = "#f43f5e";
    statusMsg.textContent = "Connection Failed!";
  }
}
