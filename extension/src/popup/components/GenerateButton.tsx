interface Props {
  onClick: () => void;
  disabled: boolean;
}

export function GenerateButton({ onClick, disabled }: Props) {
  return (
    <button onClick={onClick} disabled={disabled} style={{ ...styles.btn, ...(disabled ? styles.disabled : {}) }}>
      Generate Playlist
    </button>
  );
}

const styles: Record<string, React.CSSProperties> = {
  btn: { width: "100%", background: "#1DB954", color: "#000", border: "none", borderRadius: "24px", padding: "14px", fontSize: "15px", fontWeight: 700, cursor: "pointer" },
  disabled: { opacity: 0.4, cursor: "not-allowed" },
};
