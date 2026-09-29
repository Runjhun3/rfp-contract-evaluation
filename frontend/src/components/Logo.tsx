// The BidLens mark: a bid page under a lens.
export default function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 3h9l4 4v5" />
      <path d="M4 3v18h7" />
      <path d="M7 8h5M7 11.5h4" />
      <circle cx="16" cy="16" r="4" />
      <path d="M19 19l2.5 2.5" />
    </svg>
  );
}
