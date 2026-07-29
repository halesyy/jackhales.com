import Link from "next/link";

type aiAssistedBadgeProps = {
  /** "byline" sits inline under an article title; "tag" sits alongside status tags in a list. */
  variant?: "byline" | "tag";
};

export const aiAssistedTooltip =
  "Directed and original content. The ideas, research and conclusions are mine; AI assisted with the writing and the breakdown of the content.";

export function AiAssistedBadge({ variant = "byline" }: aiAssistedBadgeProps) {
  return (
    <Link href="/ai-assisted" className={`ai-badge ai-badge-${variant}`} aria-label={`AI-assisted. ${aiAssistedTooltip}`}>
      <span>AI-assisted</span>
      <span className="ai-badge-tip" role="tooltip">
        {aiAssistedTooltip}
        <small>Read what this means</small>
      </span>
    </Link>
  );
}
