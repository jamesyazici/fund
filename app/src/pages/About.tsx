const RESOURCES: { title: string; desc: string; href: string }[] = [
  { title: 'Investopedia — Sharpe Ratio', desc: 'Risk-adjusted return, explained.', href: 'https://www.investopedia.com/terms/s/sharperatio.asp' },
  { title: 'Hull — Options, Futures & Other Derivatives', desc: 'The standard derivatives text.', href: 'https://www.pearson.com/' },
  { title: 'Ernie Chan — Quantitative Trading', desc: 'A practical intro to systematic strategies.', href: 'https://www.epchan.com/books/' },
  { title: 'Alpaca Docs', desc: 'The trading & market-data API powering our pods.', href: 'https://docs.alpaca.markets/' },
  { title: 'QuantStart', desc: 'Articles on backtesting, execution and portfolio construction.', href: 'https://www.quantstart.com/' },
  { title: 'CFA Institute — Performance Measurement', desc: 'How professionals attribute and report returns.', href: 'https://www.cfainstitute.org/' },
]

export function About() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 py-2">
      <header className="border-b border-rule pb-4">
        <h1 className="font-serif text-5xl leading-none">About RQFC</h1>
        <p className="mt-3 text-sm leading-relaxed text-ink/90">
          RQFC is a student-run, fully transparent paper-trading fund. We run several independent strategy{' '}
          <span className="font-semibold">pods</span>, each a small team of <span className="font-semibold">traders</span>{' '}
          sharing one account. Everything you see here is live: the moment a trade clears, it is recorded and marked
          against real market data.
        </p>
      </header>

      <section>
        <h2 className="font-serif text-2xl">Mission</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink/90">
          Demystify how a quantitative fund actually works by operating one in the open. Most funds are black boxes —
          you see a monthly number and nothing else. We publish every order, every position, and every dollar of
          realized and unrealized P&amp;L, in real time, for anyone to inspect. Transparency is the product.
        </p>
      </section>

      <section>
        <h2 className="font-serif text-2xl">Objective</h2>
        <ul className="mt-2 space-y-2 text-sm leading-relaxed text-ink/90">
          <li className="border-l-2 border-rule pl-3">
            <span className="font-semibold">Educate.</span> Give students a real desk: execution, risk, attribution
            and the discipline of being measured publicly.
          </li>
          <li className="border-l-2 border-rule pl-3">
            <span className="font-semibold">Compound capital preservation, survival, and stronger risk management.</span>{' '}
            We optimize for durable, risk-adjusted returns — not headline gambles.
          </li>
          <li className="border-l-2 border-rule pl-3">
            <span className="font-semibold">Prove transparency works.</span> Show that a fund can be radically open
            without losing its edge.
          </li>
        </ul>
      </section>

      <section>
        <h2 className="font-serif text-2xl">How it works</h2>
        <ol className="mt-2 space-y-2 text-sm leading-relaxed text-ink/90">
          <li><span className="font-semibold num">1.</span> A trader places an order through the <code className="bg-panel px-1">rqfc</code> Python client.</li>
          <li><span className="font-semibold num">2.</span> Our backend checks pod membership, submits the order to Alpaca, and records the fill.</li>
          <li><span className="font-semibold num">3.</span> Positions are continuously marked to live prices — a 2% move in a holding flows straight into that pod's value.</li>
          <li><span className="font-semibold num">4.</span> This portal reads the public feed and renders it, marked to market, with no manual numbers.</li>
        </ol>
      </section>

      <section>
        <h2 className="font-serif text-2xl">Learning resources</h2>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {RESOURCES.map((r) => (
            <a
              key={r.title}
              href={r.href}
              target="_blank"
              rel="noreferrer"
              className="card-soft px-4 py-3 hover:bg-paper"
            >
              <div className="text-xs font-semibold">{r.title} ↗</div>
              <div className="mt-1 text-2xs text-faint">{r.desc}</div>
            </a>
          ))}
        </div>
      </section>

      <p className="border-t border-rule pt-4 text-2xs uppercase tracking-[0.14em] text-faint">
        Paper-traded · educational use only · not investment advice
      </p>
    </div>
  )
}
