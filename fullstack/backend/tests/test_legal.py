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
    assert '2 November 2026' in terms.text
    assert 'Privacy Notice' in privacy.text
    assert 'does not hold itself out as a SEBI-registered' in terms.text
    assert 'not an instruction to transact' in terms.text
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
    assert 'id="legal-continue" type="submit" disabled' in page.text
    assert 'href="/terms"' in page.text
    assert "if(!acknowledgement.checked)return;" in script.text
    assert "startTerminal();" in script.text
    assert 'LEGAL_NOTICE_VERSION' in script.text
    assert 'terms-pending .terminal-app' in css.text


def test_public_legal_copy_has_no_internal_implementation_notes():
    terms=client.get('/terms').text
    privacy=client.get('/privacy').text
    for text in (terms,privacy):
        assert '2 November 2026' in text
        for forbidden in (
            'No contact email is invented', 'Do not enable real-email collection',
            'secret access key', 'separate persistent database',
            'this document does not invent', 'a disclaimer alone cannot',
            'Supabase', 'backend'
        ):
            assert forbidden.lower() not in text.lower()
    assert 'Render' in privacy
    assert 'TradingView Lightweight Charts' in privacy
    assert 'not a guaranteed real-time exchange quote' in terms


def test_terminal_navigation_neutral_labels_and_risk_inputs():
    page=client.get('/terminal').text
    script=client.get('/terminal.js').text
    assert 'href="/beta">Leave Trader Mode' not in page
    assert 'href="/#/home">Return to research home' in page
    assert 'href="/#/home"' in page
    assert 'UPPER HISTORICAL BAND' in page
    assert 'LOWER HISTORICAL BAND' in page
    assert 'id="paper-capital"' in page
    assert 'id="paper-risk"' in page
    assert 'id="paper-stop"' in page
    assert 'function resetHistory()' in script
    assert 'timeoutMs:45000' in script
    assert 'researchSnapshots' in script
    assert 'localStorage.getItem(LEGAL_NOTICE_VERSION)' in script
