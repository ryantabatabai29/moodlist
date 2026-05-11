const params = new URLSearchParams(window.location.search);
const code = params.get("code");

if (code) {
  chrome.runtime.sendMessage({ type: "SPOTIFY_CALLBACK", code }, () => {
    window.close();
  });
} else {
  window.close();
}
