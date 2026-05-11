import type { GenerateResult } from "../../types";

interface Props {
  result: GenerateResult;
  onRegenerate: () => void;
}

export function ResultView({ result, onRegenerate }: Props) {
  return (
    <div style={styles.container}>
      <div style={styles.checkmark}>✓</div>
      <h2 style={styles.name}>{result.playlistName}</h2>
      <p style={styles.count}>{result.trackCount} tracks</p>
      <a href={result.playlistUrl} target="_blank" rel="noreferrer" style={styles.openBtn}>
        Open in Spotify
      </a>
      <button onClick={onRegenerate} style={styles.regenBtn}>
        Generate another
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "12px", textAlign: "center" },
  checkmark: { fontSize: "48px", color: "#1DB954" },
  name: { fontSize: "16px", fontWeight: 700, color: "#fff", maxWidth: "280px" },
  count: { color: "#aaa", fontSize: "13px" },
  openBtn: { display: "inline-block", background: "#1DB954", color: "#000", textDecoration: "none", borderRadius: "24px", padding: "12px 28px", fontWeight: 700, fontSize: "14px" },
  regenBtn: { background: "none", border: "1px solid #444", color: "#aaa", borderRadius: "24px", padding: "8px 20px", fontSize: "13px", cursor: "pointer" },
};
