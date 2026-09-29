// The right half of the sign-in page: what BidLens does, in one picture. Decorative:
// the words beside it say the same thing, so the SVG is hidden from screen readers.
const LINES = [[64, 150], [64, 190], [64, 120], [64, 176], [64, 96]];

function BidPage() {
  return (
    <g>
      <rect x="62" y="84" width="250" height="330" rx="10" fill="#2E3B48" transform="rotate(-6 187 249)" />
      <rect x="96" y="58" width="258" height="342" rx="10" fill="#FFFFFF" />
      <text x="120" y="92" className="art-cap">BIDDER B · TECHNICAL BID</text>
      <text x="120" y="118" className="art-title">Credential 04</text>
      {LINES.map(([x, w], i) => <rect key={i} x={x + 56} y={138 + i * 18} width={w} height="7" rx="3.5" fill="#E6E3DA" />)}
      <rect x="112" y="236" width="226" height="30" rx="6" fill="#FBEBD7" />
      <text x="122" y="256" className="art-quote">Project value ₹5.89 Cr</text>
      {[0, 1, 2, 3].map((i) => <rect key={i} x="120" y={286 + i * 18} width={[168, 196, 132, 184][i]} height="7" rx="3.5" fill="#E6E3DA" />)}
      <text x="330" y="386" className="art-cap" textAnchor="end">PDF p. 212</text>
    </g>
  );
}

function Lens() {
  return (
    <g className="art-lens">
      <line x1="330" y1="304" x2="372" y2="346" stroke="#C9CED4" strokeWidth="14" strokeLinecap="round" />
      <circle cx="286" cy="252" r="66" fill="#EEF3FA" stroke="#F6F5F1" strokeWidth="6" />
      <text x="286" y="248" className="art-lens-big" textAnchor="middle">₹5.89 Cr</text>
      <text x="286" y="270" className="art-cap" textAnchor="middle">QUOTE FOUND ✓</text>
    </g>
  );
}

function ScoreCard() {
  return (
    <g>
      <path d="M338 214 C 372 180, 380 150, 404 142" fill="none" stroke="#7FA3D1" strokeWidth="2" strokeDasharray="5 6" />
      <rect x="404" y="70" width="214" height="150" rx="12" fill="#FFFFFF" />
      <text x="424" y="100" className="art-cap">CRITERION A.2 · ≥ ₹1 CR</text>
      <text x="424" y="140" className="art-score">2<tspan className="art-of"> / 2 marks</tspan></text>
      <text x="424" y="172" className="art-ok">✓ Quote on the cited page</text>
      <text x="424" y="196" className="art-ok">✓ Value re-read by Python</text>
    </g>
  );
}

const RESULTS: [string, string, boolean][] = [["Bidder A", "60", false], ["Bidder B", "65", false], ["Bidder C", "64.5", true]];

function Results() {
  return (
    <g>
      <rect x="404" y="244" width="214" height="156" rx="12" fill="#FFFFFF" />
      <text x="424" y="274" className="art-cap">RESULTS · DOCUMENTS /65</text>
      {RESULTS.map(([name, marks, review], i) => (
        <g key={name}>
          <line x1="424" x2="598" y1={292 + i * 34} y2={292 + i * 34} stroke="#E6E3DA" />
          <text x="424" y={314 + i * 34} className="art-row">{name}</text>
          {review && <rect x="514" y={299 + i * 34} width="84" height="22" rx="11" fill="#FBEBD7" />}
          <text x="590" y={314 + i * 34} className={review ? "art-row art-review" : "art-row"} textAnchor="end">
            {review ? "● " : ""}{marks}
          </text>
        </g>
      ))}
    </g>
  );
}

export default function LoginArt() {
  return (
    <aside className="login-art">
      <div className="login-art-copy">
        <p className="eyebrow">RFP bid evaluation</p>
        <h2>Every mark, traced to its page.</h2>
        <p>BidLens reads each bid against the RFP's own rules, quotes the evidence it relied on,
          and leaves every judgement call to the committee.</p>
      </div>
      <svg className="login-illustration" viewBox="40 40 600 390" role="presentation" aria-hidden="true">
        <BidPage />
        <ScoreCard />
        <Results />
        <Lens />
      </svg>
      <ul className="login-points">
        <li><span>01</span>Quotes checked on the cited page</li>
        <li><span>02</span>Best items counted, totals re-added</li>
        <li><span>03</span>Committee decides every flag</li>
      </ul>
    </aside>
  );
}
