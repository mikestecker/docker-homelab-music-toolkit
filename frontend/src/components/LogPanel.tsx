export default function LogPanel({ lines }: { lines: string[] | undefined }) {
  if (!lines || lines.length === 0) return null;
  return <div className="log">{lines.join("\n")}</div>;
}
