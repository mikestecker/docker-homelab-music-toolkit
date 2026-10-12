import { diffAgainst } from "../../lib/diff";

/** Renders `value` with the parts that differ from `reference` wrapped in
 * <mark>. Renders plain text (no diffing) when there's nothing to compare
 * against, so a lone copy with no siblings looks like ordinary text. */
export default function DiffText({ value, reference }: { value: string; reference?: string }) {
  if (!reference) return <>{value}</>;
  return (
    <>
      {diffAgainst(value, reference).map((seg, i) =>
        seg.changed ? <mark key={i}>{seg.text}</mark> : <span key={i}>{seg.text}</span>,
      )}
    </>
  );
}
