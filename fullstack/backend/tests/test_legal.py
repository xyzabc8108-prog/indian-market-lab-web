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
    assert '02/11/2026' in terms.text
    assert 'Privacy Notice' in privacy.text
    assert 'not presented as a SEBI-registered' in terms.text
    assert 'not personalized instructions' in terms.text
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
