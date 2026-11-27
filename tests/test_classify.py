from bs4 import BeautifulSoup

from conftest import FIXTURES
from outreach.classify import ELEMENTOR, HTML_FORM, READY, UNCLEAR, build_plan
from outreach.finder import choose_form

PAGE = "https://www.example.co.il/contact/"


def plan_for(fixture: str, page_url: str = PAGE):
    soup = BeautifulSoup((FIXTURES / fixture).read_text(encoding="utf-8"), "lxml")
    form, _ = choose_form(soup)
    assert form is not None, f"no usable form chosen in {fixture}"
    return build_plan(form, page_url)


def roles(plan) -> dict[str, str]:
    return {f.name: f.role for f in plan.fields}


def test_contact_form_7_hebrew() -> None:
    r = plan_for("cf7_hebrew.html")
    assert r.status == READY, r.detail
    p = r.plan
    assert roles(p) == {"your-name": "name", "your-email": "email", "your-tel": "phone",
                        "your-subject": "subject", "your-message": "message", "acceptance-1": "consent"}
    assert p.action_url == "https://www.example.co.il/contact/#wpcf7-f42-p7-o1"
    assert p.method == "post" and p.encoding == "application/x-www-form-urlencoded"
    assert p.hidden_fields == {"_wpcf7": "42", "_wpcf7_version": "5.8.4", "_wpcf7_locale": "he_IL",
                               "_wpcf7_unit_tag": "wpcf7-f42-p7-o1", "_wpcf7_container_post": "7"}
    required = {f.name for f in p.fields if f.required}
    assert required == {"your-name", "your-email"}
    consent = next(f for f in p.fields if f.role == "consent")
    assert consent.value == "1" and consent.required is False
    assert p.honeypots == []


def test_elementor_form() -> None:
    r = plan_for("elementor.html")
    assert r.status == READY, r.detail
    assert roles(r.plan) == {"form_fields[name]": "name", "form_fields[email]": "email",
                             "form_fields[field_phone]": "phone", "form_fields[message]": "message"}
    assert set(r.plan.hidden_fields) == {"post_id", "form_id", "referer_title", "queried_id"}
    # Not the page itself: Elementor handles the form only at the AJAX address the page states.
    assert r.plan.action_url == "https://www.example.co.il/wp-admin/admin-ajax.php"
    assert r.plan.handler == ELEMENTOR
    assert r.plan.encoding == "multipart/form-data" and r.plan.charset == "utf-8"
    assert "Elementor form" in r.plan.summary()


def elementor_html(config: str | None) -> str:
    html = (FIXTURES / "elementor.html").read_text(encoding="utf-8")
    start = html.index('<script id="elementor-pro-frontend-js-before">')
    end = html.index("</script>", start) + len("</script>")
    return html[:start] + (f"<script>{config}</script>" if config is not None else "") + html[end:]


def plan_for_html(html: str, page_url: str = PAGE):
    form, _ = choose_form(BeautifulSoup(html, "lxml"))
    assert form is not None
    return build_plan(form, page_url)


def test_elementor_absolute_escaped_ajaxurl_as_real_sites_print_it() -> None:
    cfg = 'var ElementorProFrontendConfig = {"ajaxurl":"https:\\/\\/www.example.co.il\\/wp-admin\\/admin-ajax.php"};'
    r = plan_for_html(elementor_html(cfg))
    assert r.status == READY, r.detail
    assert r.plan.action_url == "https://www.example.co.il/wp-admin/admin-ajax.php"


def test_elementor_without_stated_ajaxurl_is_unclear_not_guessed() -> None:
    for cfg in (None, 'var elementorFrontendConfig = {"environmentMode":{}};',
                'var ElementorProFrontendConfig = {"nonce":"x"};'):
        r = plan_for_html(elementor_html(cfg))
        assert r.status == UNCLEAR and "AJAX address" in r.detail, cfg


def test_elementor_ajaxurl_on_another_domain_is_unclear() -> None:
    cfg = 'var ElementorProFrontendConfig = {"ajaxurl":"https:\\/\\/evil.example.com\\/wp-admin\\/admin-ajax.php"};'
    r = plan_for_html(elementor_html(cfg))
    assert r.status == UNCLEAR and "another domain" in r.detail


def test_elementor_form_without_form_id_is_unclear() -> None:
    html = (FIXTURES / "elementor.html").read_text(encoding="utf-8").replace(
        '<input type="hidden" name="form_id" value="4f1a2b3">', "")
    r = plan_for_html(html)
    assert r.status == UNCLEAR and "form_id" in r.detail


def test_non_elementor_form_keeps_html_handler() -> None:
    r = plan_for("cf7_hebrew.html")
    assert r.plan.handler == HTML_FORM


def test_plain_english_form_and_search_form_excluded() -> None:
    r = plan_for("plain_english.html")
    assert r.status == READY, r.detail
    assert roles(r.plan) == {"fullname": "name", "email": "email", "phone": "phone", "subject": "subject",
                             "message": "message"}
    assert r.plan.action_url == "https://www.example.co.il/contact/send"
    assert r.plan.hidden_fields == {"csrf_token": "abc123"}
    assert r.plan.ignored_optional == ["referral"]  # optional unknown select left empty
    assert r.plan.submit == ("send", "1")
    assert r.plan.method == "post"  # "POST" in the HTML is normalized


def test_honeypot_fields_left_empty_and_hidden_tokens_kept() -> None:
    r = plan_for("honeypot.html")
    assert r.status == READY, r.detail
    assert set(r.plan.honeypots) == {"website", "company_hp", "url_check"}
    assert set(roles(r.plan)) == {"name", "email", "message"}
    assert r.plan.hidden_fields == {"nonce": "n-9f8e7d"}


def test_unknown_required_field_gives_unclear_fields() -> None:
    r = plan_for("unknown_required.html")
    assert r.status == UNCLEAR
    assert "id_number" in r.detail and "branch" in r.detail


def test_cross_domain_action_gives_unclear_fields() -> None:
    r = plan_for("cross_domain.html")
    assert r.status == UNCLEAR
    assert "another domain" in r.detail and "forms.other-service.example" in r.detail


def test_same_site_subdomain_action_is_allowed() -> None:
    html = ('<form action="https://forms.example.co.il/send" method="post">'
            '<input name="email" type="email"><textarea name="message"></textarea></form>')
    form = BeautifulSoup(html, "lxml").find("form")
    assert build_plan(form, PAGE).status == READY


def test_get_method_gives_unclear_fields() -> None:
    html = '<form action="/c" method="get"><input name="email" type="email"><textarea name="m"></textarea></form>'
    r = build_plan(BeautifulSoup(html, "lxml").find("form"), PAGE)
    assert r.status == UNCLEAR and "method" in r.detail


def test_form_without_message_field_gives_unclear_fields() -> None:
    html = ('<form method="post"><input name="name" type="text" required>'
            '<input name="email" type="email" required><input name="phone" type="tel"></form>')
    r = build_plan(BeautifulSoup(html, "lxml").find("form"), PAGE)
    assert r.status == UNCLEAR and "message" in r.detail


def test_company_field_is_not_mistaken_for_name() -> None:
    html = ('<form method="post"><label for="c">שם החברה *</label><input id="c" name="company">'
            '<input name="email" type="email"><textarea name="message"></textarea></form>')
    r = build_plan(BeautifulSoup(html, "lxml").find("form"), PAGE)
    assert r.status == UNCLEAR and "company" in r.detail


def test_first_and_last_name_parts() -> None:
    html = ('<form method="post"><input name="first_name" placeholder="שם פרטי">'
            '<input name="last_name" placeholder="שם משפחה"><input name="email" type="email">'
            '<textarea name="message"></textarea></form>')
    r = build_plan(BeautifulSoup(html, "lxml").find("form"), PAGE)
    parts = {f.name: f.part for f in r.plan.fields if f.role == "name"}
    assert parts == {"first_name": "first", "last_name": "last"}


def test_summary_is_human_readable() -> None:
    text = plan_for("cf7_hebrew.html").plan.summary()
    assert "submits to: https://www.example.co.il/contact/#wpcf7-f42-p7-o1 (POST" in text
    assert "fill 'your-email' as email (required)" in text
    assert "keep hidden: _wpcf7" in text
