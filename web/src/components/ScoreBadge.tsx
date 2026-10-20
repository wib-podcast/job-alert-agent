/**
 * The score is the first thing you look at, so it gets the only strong colour
 * on the card. Bands match the digest's threshold: 7.0 is "worth opening".
 */
export function ScoreBadge({ score }: { score: number }) {
  const band = score >= 8 ? "high" : score >= 7 ? "mid" : "low";
  const colour =
    band === "high"
      ? "text-score-high"
      : band === "mid"
        ? "text-score-mid"
        : "text-score-low";

  return (
    <span
      className={`shrink-0 font-mono text-lg font-semibold tabular-nums ${colour}`}
      title={`Relevance ${score.toFixed(1)} of 10`}
    >
      {score > 0 ? score.toFixed(1) : "—"}
    </span>
  );
}
