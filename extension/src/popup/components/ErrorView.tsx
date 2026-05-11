import type { ErrorType } from "../../types";

interface Props {
  errorType: ErrorType;
  onRetry: () => void;
}

const ERROR_MESSAGES: Record<ErrorType, { title: string; detail: string }> = {
  auth_failure: {
    title: "Authentication failed",
    detail: "Your Spotify session expired. Please reconnect.",
  },
  rate_limit: {
    title: "Spotify rate limit",
    detail: "Too many requests. Please wait a moment and try again.",
  },
  empty_result: {
    title: "No matches found",
    detail: "Try a different prompt or select a larger playlist.",
  },
  server_error: {
    title: "Something went wrong",
    detail: "The server encountered an error. Please try again.",
  },
  lyrics_unavailable: {
    title: "Lyrics unavailable",
    detail: "Lyrics could not be fetched; results are based on genre and metadata only.",
  },
};

export function ErrorView({ errorType, onRetry }: Props) {
  const { title, detail } = ERROR_MESSAGES[errorType];
  return (
    <div style={styles.container}>
      <div style={styles.icon}>✕</div>
      <h2 style={styles.title}>{title}</h2>
      <p style={styles.detail}>{detail}</p>
      <button onClick={onRetry} style={styles.retryBtn}>
        Try again
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "12px", textAlign: "center" },
  icon: { fontSize: "48px", color: "#e55" },
  title: { fontSize: "16px", fontWeight: 700, color: "#fff" },
  detail: { color: "#aaa", fontSize: "13px", maxWidth: "260px" },
  retryBtn: { background: "#1DB954", color: "#000", border: "none", borderRadius: "24px", padding: "12px 28px", fontWeight: 700, fontSize: "14px", cursor: "pointer" },
};
