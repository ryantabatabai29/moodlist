interface Props {
  value: number;
  onChange: (value: number) => void;
}

export function SizeSlider({ value, onChange }: Props) {
  return (
    <div>
      <label style={styles.label}>
        Tracks: <strong style={styles.count}>{value}</strong>
      </label>
      <input
        type="range"
        min={10}
        max={50}
        step={5}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={styles.slider}
      />
      <div style={styles.range}>
        <span>10</span>
        <span>50</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  label: { display: "block", color: "#aaa", fontSize: "12px", marginBottom: "6px" },
  count: { color: "#1DB954" },
  slider: { width: "100%", accentColor: "#1DB954" },
  range: { display: "flex", justifyContent: "space-between", color: "#666", fontSize: "11px", marginTop: "2px" },
};
