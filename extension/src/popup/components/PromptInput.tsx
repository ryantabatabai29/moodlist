interface Props {
  value: string;
  onChange: (value: string) => void;
}

const EXAMPLES = ["hype", "late-night drive", "focus instrumental", "chill Sunday morning"];

export function PromptInput({ value, onChange }: Props) {
  return (
    <div>
      <label style={styles.label}>Mood or vibe</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`e.g. "${EXAMPLES[Math.floor(Math.random() * EXAMPLES.length)]}"`}
        style={styles.input}
        maxLength={120}
        autoFocus
      />
      <div style={styles.chips}>
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => onChange(ex)} style={styles.chip}>
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  label: { display: "block", color: "#aaa", fontSize: "12px", marginBottom: "6px" },
  input: { width: "100%", background: "#282828", color: "#fff", border: "1px solid #444", borderRadius: "6px", padding: "8px 10px", fontSize: "14px", outline: "none" },
  chips: { display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" },
  chip: { background: "#333", color: "#ccc", border: "none", borderRadius: "12px", padding: "4px 10px", fontSize: "12px", cursor: "pointer" },
};
