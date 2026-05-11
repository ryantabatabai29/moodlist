import { useEffect, useState } from "react";
import { getAccessToken, logout, startAuthFlow } from "../auth/auth";
import { generatePlaylist, getPlaylists } from "../api/backend";
import type { ErrorType, GenerateResult, PlaylistItem, PopupState } from "../types";
import { PlaylistSelector } from "./components/PlaylistSelector";
import { PromptInput } from "./components/PromptInput";
import { SizeSlider } from "./components/SizeSlider";
import { GenerateButton } from "./components/GenerateButton";
import { ResultView } from "./components/ResultView";
import { ErrorView } from "./components/ErrorView";

export function Popup() {
  const [state, setState] = useState<PopupState>("unauthenticated");
  const [playlists, setPlaylists] = useState<PlaylistItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [prompt, setPrompt] = useState<string>("");
  const [size, setSize] = useState<number>(20);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [errorType, setErrorType] = useState<ErrorType | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  useEffect(() => {
    getAccessToken().then((token) => {
      if (token) {
        setAccessToken(token);
        setState("idle");
        loadPlaylists(token);
      } else {
        setState("unauthenticated");
      }
    });

    // Listen for auth completion from background service worker
    const handler = (msg: { type: string }) => {
      if (msg.type === "AUTH_COMPLETE") {
        getAccessToken().then((token) => {
          if (token) {
            setAccessToken(token);
            setState("idle");
            loadPlaylists(token);
          }
        });
      }
    };
    chrome.runtime.onMessage.addListener(handler);
    return () => chrome.runtime.onMessage.removeListener(handler);
  }, []);

  async function loadPlaylists(token: string) {
    try {
      const items = await getPlaylists(token);
      setPlaylists(items);
      if (items.length > 0) setSelectedId(items[0].id);
    } catch {
      setErrorType("server_error");
      setState("error");
    }
  }

  async function handleGenerate() {
    if (!accessToken || !selectedId || !prompt.trim()) return;
    setState("loading");
    try {
      const res = await generatePlaylist(accessToken, selectedId, prompt.trim(), size);
      setResult(res);
      setState("result");
    } catch (err) {
      const e = err as Error & { errorType?: ErrorType };
      setErrorType(e.errorType ?? "server_error");
      setState("error");
    }
  }

  function handleRetry() {
    setState("idle");
    setErrorType(null);
    setResult(null);
  }

  async function handleLogout() {
    await logout();
    setAccessToken(null);
    setState("unauthenticated");
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <span style={styles.logo}>🎵 Moodlist</span>
        {state !== "unauthenticated" && (
          <button onClick={handleLogout} style={styles.logoutBtn}>
            Disconnect
          </button>
        )}
      </header>

      {state === "unauthenticated" && (
        <div style={styles.center}>
          <p style={styles.tagline}>Generate mood-based playlists from your Spotify library.</p>
          <button onClick={startAuthFlow} style={styles.connectBtn}>
            Connect Spotify
          </button>
        </div>
      )}

      {state === "idle" && (
        <div style={styles.form}>
          <PlaylistSelector playlists={playlists} value={selectedId} onChange={setSelectedId} />
          <PromptInput value={prompt} onChange={setPrompt} />
          <SizeSlider value={size} onChange={setSize} />
          <GenerateButton onClick={handleGenerate} disabled={!prompt.trim() || !selectedId} />
        </div>
      )}

      {state === "loading" && (
        <div style={styles.center}>
          <div style={styles.spinner} />
          <p style={styles.loadingText}>Generating your playlist…</p>
          <p style={styles.subText}>Up to 15 seconds for a cold start</p>
        </div>
      )}

      {state === "result" && result && (
        <ResultView result={result} onRegenerate={handleRetry} />
      )}

      {state === "error" && (
        <ErrorView errorType={errorType ?? "server_error"} onRetry={handleRetry} />
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: "16px", minHeight: "480px", display: "flex", flexDirection: "column", gap: "12px" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  logo: { fontSize: "18px", fontWeight: 700, color: "#1DB954" },
  logoutBtn: { background: "none", border: "none", color: "#aaa", cursor: "pointer", fontSize: "12px" },
  center: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "16px", textAlign: "center" },
  tagline: { color: "#aaa", fontSize: "14px", maxWidth: "260px" },
  connectBtn: { background: "#1DB954", color: "#000", border: "none", borderRadius: "24px", padding: "12px 32px", fontSize: "15px", fontWeight: 700, cursor: "pointer" },
  form: { display: "flex", flexDirection: "column", gap: "16px" },
  spinner: { width: "32px", height: "32px", border: "3px solid #333", borderTop: "3px solid #1DB954", borderRadius: "50%", animation: "spin 0.8s linear infinite" },
  loadingText: { color: "#fff", fontWeight: 600 },
  subText: { color: "#aaa", fontSize: "12px" },
};
