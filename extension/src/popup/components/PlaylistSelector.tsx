import type { PlaylistItem } from "../../types";

interface Props {
  playlists: PlaylistItem[];
  value: string;
  onChange: (id: string) => void;
}

export function PlaylistSelector({ playlists, value, onChange }: Props) {
  return (
    <div>
      <label style={styles.label}>Source playlist</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} style={styles.select}>
        {playlists.map((pl) => (
          <option key={pl.id} value={pl.id}>
            {pl.name} ({pl.trackCount} tracks)
          </option>
        ))}
      </select>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  label: { display: "block", color: "#aaa", fontSize: "12px", marginBottom: "6px" },
  select: { width: "100%", background: "#282828", color: "#fff", border: "1px solid #444", borderRadius: "6px", padding: "8px 10px", fontSize: "14px", cursor: "pointer" },
};
