"""Public disclaimer routes and Trader Mode acknowledgement contracts."""
from fastapi.testclient import TestClient
from fullstack.backend.main import app

client = TestClient(app)


def test_legal_pages_are_public_and_readable():
    terms = client.get('/terms')
    privacy = client.get('/privacy')
    css = client.get('/legal.css')
    assert terms.status_code == 200 and privacy.status_code == 200
    assert css.status_code == 200
    assert 'Disclaimer &amp; Terms of Use' in terms.text
    assert 'November 2, 2026' in terms.text
    assert 'Privacy Notice' in privacy.text
    assert 'not registered with SEBI as a Research Analyst' in terms.text
    assert 'None of these outputs is intended as an instruction' in terms.text
    assert 'beta_waitlist' not in terms.text


def test_app_and_beta_show_research_risks():
    dashboard = client.get('/app.js')
    beta = client.get('/beta')
    assert dashboard.status_code == 200 and beta.status_code == 200
    assert 'global-disclosure' in dashboard.text
    assert 'href="/terms"' in dashboard.text
    assert 'href="/privacy"' in dashboard.text
    assert 'beta-disclosure' in beta.text
    assert 'href="/terms"' in beta.text
    assert 'href="/privacy"' in beta.text


def test_terminal_acknowledgement_is_explicit_and_blocks_interaction():
    page = client.get('/terminal')
    script = client.get('/terminal.js')
    css = client.get('/terminal.css')
    assert page.status_code == 200
    assert script.status_code == 200 and css.status_code == 200
    assert 'id="legal-gate"' in page.text
    assert 'id="terminal-interactive" inert' in page.text
    assert 'id="legal-acknowledge" required' in page.text
    assert 'id="legal-continue" type="submit" disabled>I Understand — Enter Terminal' in page.text
    assert 'href="/terms"' in page.text
    assert "if(!acknowledgement.checked)return;" in script.text
    assert "startTerminal();" in script.text
    assert 'LEGAL_NOTICE_VERSION' in script.text
    assert 'terms-pending .terminal-app' in css.text


def test_public_legal_copy_has_no_internal_implementation_notes():
    terms=client.get('/terms').text
    privacy=client.get('/privacy').text
    for text in (terms,privacy):
        assert 'November 2, 2026' in text
        for forbidden in (
            'No contact email is invented', 'Do not enable real-email collection',
            'secret access key', 'separate persistent database',
            'this document does not invent', 'a disclaimer alone cannot',
            'Supabase', 'backend'
        ):
            assert forbidden.lower() not in text.lower()
    assert 'Render' in privacy
    assert 'TradingView Lightweight Charts' in privacy
    assert 'does not provide exchange-verified live tick feeds' in terms


def test_terminal_navigation_neutral_labels_and_risk_inputs():
    page=client.get('/terminal').text
    script=client.get('/terminal.js').text
    assert 'href="/beta">Leave Trader Mode' not in page
    assert 'href="/#/home">Return to research home' in page
    assert 'href="/#/home"' in page
    assert 'UPPER VOLATILITY RANGE (90th %)' in page
    assert 'LOWER VOLATILITY RANGE (10th %)' in page
    assert 'id="paper-capital"' in page
    assert 'id="paper-risk"' in page
    assert 'id="paper-stop"' in page
    assert 'function resetHistory()' in script
    assert 'timeoutMs:45000' in script
    assert 'researchSnapshots' in script
    assert 'sessionStorage.getItem(LEGAL_NOTICE_VERSION)' in script


def test_watchlist_recovery_and_range_selection_contract():
    page=client.get('/terminal').text
    js=client.get('/terminal.js').text
    assert 'id="watch-retry"' in page
    assert 'id="terminal-symbol"' in page
    assert 'watchSlowTimer=setTimeout(' in js
    assert '},5000);' in js
    assert "'1m':['1d','5d']" in js
    assert "'5m':['1d','5d']" in js
    assert "'15m':['1wk','1mo']" in js
    assert "'1h':['1wk','1mo']" in js
    assert "'1d':['3mo','6mo','1y']" in js
    assert "'1wk':['1y','3y','5y']" in js
    assert 'Last candle:' in js


def test_operator_identity_and_legal_references_present():
    terms=client.get('/terms').text
    privacy=client.get('/privacy').text
    for page in (terms, privacy):
        assert 'Rohan Chhaya' in page
        assert 'Rajkot, Gujarat, India' in page
        assert 'November 2, 2026' in page
        assert '[your-email@domain.com]' not in page
    assert 'competent courts located in' in terms
    assert 'NSE Data Usage Policy' in terms


def test_official_contact_email_published_on_both_pages():
    privacy = client.get('/privacy')
    terms = client.get('/terms')
    assert privacy.status_code == 200 and terms.status_code == 200
    email_link = 'href="mailto:rohanchhaya108@gmail.com"'
    assert email_link in privacy.text
    assert email_link in terms.text
    assert 'rohanchhaya108@gmail.com</a>' in privacy.text
    assert 'Our verified contact email will be available' not in privacy.text
    assert privacy.headers.get('cache-control') == 'no-store'


def test_legal_home_links_and_live_beta_form_status_copy():
    privacy=client.get('/privacy').text
    terms=client.get('/terms').text
    for page in (privacy,terms):
        assert 'href="/#/home"' in page
        assert 'Return to research home' in page
        assert 'href="/beta"' in page
        assert 'currently closed' not in page
    assert 'href="/beta#join"' in privacy
    assert 'href="/beta#feedback"' in privacy
    assert 'href="mailto:rohanchhaya108@gmail.com"' in privacy
    assert 'when the contact channel is available' not in privacy
    assert 'Public Beta page' in terms


def test_terminal_modals_banners_and_initial_ranges_match():
    html=client.get('/terminal').text
    assert 'bull/bear scenarios and hypothetical price levels' not in html
    assert 'illustrative price levels and scenario outputs' not in html
    assert html.count('candlestick patterns and statistical volatility ranges')>=1
    assert 'Candlestick patterns and statistical volatility ranges' in html
    assert '<select id="chart-lookback"' in html
    assert '<option value="3mo">3 months</option>' in html
    assert '<option value="6mo" selected>6 months</option>' in html
    assert '<option value="1y">1 year</option>' in html
    script=client.get('/terminal.js').text
    assert "resetHistory();loadTerminal();" in script
    assert "const select=$('chart-lookback'),ranges=RANGES[state.interval];" in script


def test_feedback_widget_exists_on_both_market_workspaces():
    homepage=client.get('/').text
    terminal=client.get('/terminal').text
    widget=client.get('/feedback-widget.js')
    stylesheet=client.get('/feedback-widget.css')
    assert widget.status_code == stylesheet.status_code == 200
    assert '/feedback-widget.js?v=1' in homepage
    assert '/feedback-widget.js?v=1' in terminal
    assert '/feedback-widget.css?v=1' in homepage
    assert '/feedback-widget.css?v=1' in terminal
    assert '/api/beta/status' in widget.text
    assert '/api/beta/feedback' in widget.text
    assert 'data.feedback_open===true' in widget.text
    assert "send.disabled=!canSend" in widget.text
    assert 'In-site feedback is not accepting submissions yet' in widget.text
    assert 'rohanchhaya108@gmail.com' in widget.text


def test_research_note_is_downloaded_locally_without_exposing_private_data():
    terminal=client.get('/terminal').text
    script=client.get('/terminal.js').text
    assert 'id="export-research-note"' in terminal
    assert 'id="export-result"' in terminal
    assert 'function buildStudyNote()' in script
    assert 'function saveStudyNote()' in script
    assert 'new Blob([note]' in script
    assert 'URL.createObjectURL(blob)' in script
    assert "state.cachedSnapshot=true" in script
    assert 'Lower volatility range (10th percentile)' in script
    assert 'Upper volatility range (90th percentile)' in script
    assert "'export-research-note').disabled=true" in script
