import {metric} from '../api.js';
export function render(){return `<div class="hero"><span class="eyebrow">MARKET RESEARCH, REIMAGINED</span><h1>Your market research.<br><em>Clear and simple.</em></h1><p>Navigate specialized tools for NSE equities, indices, F&O risk, news and paper-trading. All analyses are educational, without real order execution.</p><a class="primary-link" href="#/stocks">Research a stock →</a><a class="secondary-link" href="#/scanner">Open market scanner ↗</a><a class="secondary-link" href="/terminal">🐂 Enter Trader Mode ↗</a></div>
<div class="section-title"><div><h2>Research workspace</h2><p>Choose a dedicated section to get started. Pick what you want to explore.</p></div></div>
<div class="feature-grid">
<a class="feature" href="#/stocks"><span class="feature-icon">↗</span><strong>Stock Research</strong><p>Search stocks, review technical conditions and build risk-controlled paper plans.</p><span>EXPLORE →</span></a>
<a class="feature" href="#/scanner"><span class="feature-icon">◎</span><strong>Market Scanner</strong><p>Upload NSE daily price history and rank covered equities with transparent indicators.</p><span>EXPLORE →</span></a>
<a class="feature" href="#/indices"><span class="feature-icon">▦</span><strong>Indices</strong><p>Separate index directory, with research prices only where provider mapping is known.</p><span>EXPLORE →</span></a>
<a class="feature" href="#/derivatives"><span class="feature-icon">≋</span><strong>F&O Planner</strong><p>Illustrate options premium-at-risk and futures margin/stop budgeting.</p><span>EXPLORE →</span></a>
<a class="feature" href="#/news"><span class="feature-icon">◷</span><strong>News Intelligence</strong><p>Source-linked financial headlines and possible sector exposure—never certainty.</p><span>EXPLORE →</span></a>
<a class="feature" href="#/paper"><span class="feature-icon">▤</span><strong>Paper Portfolio</strong><p>Keep a browser-only hypothetical trade journal, export it, and review the budget.</p><span>EXPLORE →</span></a></div>
<div class="metrics-row">${metric('Paper account','₹50,000','Default, adjustable')}${metric('Planned risk','1%','₹500 per idea')}${metric('Trading execution','OFF','No brokerage login')}</div>
<div class="notice">Prices and news may be delayed. Use this website to explore and practice, not to place real trades.</div>`}
