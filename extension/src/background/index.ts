import { exchangeCode } from "../auth/auth";

chrome.runtime.onMessage.addListener(
  (message: { type: string; code: string }, _sender, sendResponse) => {
    if (message.type === "SPOTIFY_CALLBACK") {
      exchangeCode(message.code)
        .then(() => sendResponse({ success: true }))
        .catch(() => sendResponse({ success: false }));
      return true; // keep message channel open for async response
    }
  },
);
