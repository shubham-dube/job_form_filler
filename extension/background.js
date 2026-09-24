// FormFiller AI - Background Service Worker (Manifest V3)

chrome.runtime.onInstalled.addListener(() => {
  console.log("[FormFiller AI] Extension installed.");
  chrome.storage.sync.get(["serverUrl"], (result) => {
    if (!result.serverUrl) {
      chrome.storage.sync.set({
        serverUrl: "http://localhost:8000"
      });
    }
  });
});
