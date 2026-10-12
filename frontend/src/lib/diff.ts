// Word-level diff for comparing two similar strings (filenames, edition
// folder names) - so "feat." vs "ft." or a curly vs straight apostrophe is
// visually obvious instead of requiring the reader to spot it themselves.
// A small LCS (longest common subsequence) over word/whitespace/punctuation
// tokens, ported from the same technique docker-music-dupes' frontend used
// (app/index.html's tokens()/diffPair()), framework-agnostic here so it's
// just a pure function the renderer wraps in <mark>.

export interface DiffSegment {
  text: string;
  changed: boolean;
}

function tokens(s: string): string[] {
  return s.match(/[A-Za-z0-9]+|[^A-Za-z0-9]+/g) ?? [];
}

function lcsTable(a: string[], b: string[]): number[][] {
  const dp: number[][] = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  return dp;
}

function diffTokens(a: string[], b: string[]): { aOut: DiffSegment[]; bOut: DiffSegment[] } {
  const dp = lcsTable(a, b);
  const aOut: DiffSegment[] = [];
  const bOut: DiffSegment[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      aOut.push({ text: a[i], changed: false });
      bOut.push({ text: b[j], changed: false });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      aOut.push({ text: a[i], changed: true });
      i++;
    } else {
      bOut.push({ text: b[j], changed: true });
      j++;
    }
  }
  while (i < a.length) {
    aOut.push({ text: a[i], changed: true });
    i++;
  }
  while (j < b.length) {
    bOut.push({ text: b[j], changed: true });
    j++;
  }
  return { aOut, bOut };
}

/** Diff `value` against `reference`, returning segments for `value` only -
 * for rendering one of several sibling strings against "the others", pick a
 * stable reference (e.g. the first sibling) and diff every sibling against it. */
export function diffAgainst(value: string, reference: string): DiffSegment[] {
  if (value === reference) return [{ text: value, changed: false }];
  return diffTokens(tokens(value), tokens(reference)).aOut;
}
