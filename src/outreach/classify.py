"""Rule-based classification of contact-form fields (Hebrew and English).

build_plan(form, page_url) -> PlanResult(status, plan, detail)

Roles: name, email, phone, subject, message, consent (checkbox), hidden.
- Hidden inputs (tokens) are kept in the plan with their values.
- Honeypots (CSS-hidden, hidden attribute, aria-hidden, off-screen, or
  tabindex=-1 text inputs) are recorded and left EMPTY.
- A REQUIRED field that cannot be classified gives `unclear_fields`; the
  classifier never guesses.
- The form must submit to the same registrable domain as the page, with
  method post and a normal encoding; otherwise `unclear_fields`.
This module only reads HTML. It never sends anything.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from urllib.parse import urljoin, urlsplit

from bs4 import Tag

from .normalize import registrable_domain

READY = "ready"
UNCLEAR = "unclear_fields"

_HEB = "א-ת"


def _kw(*words: str) -> re.Pattern[str]:
    """English words match on word boundaries; Hebrew words may carry a one-letter prefix (ה, ו, ב, ל, מ, ש)."""
    parts = []
    for w in words:
        if re.search(f"[{_HEB}]", w):
            parts.append(f"(?<![{_HEB}])[הובלמש]?{re.escape(w)}(?![{_HEB}])")
        else:
            parts.append(rf"\b{re.escape(w)}\b")
    return re.compile("|".join(parts), re.I)


EMAIL = _kw("email", "e mail", "mail", "your email", "אימייל", "אי מייל", "מייל", 'דוא"ל', "דואל", "דואר אלקטרוני")
PHONE = _kw("phone", "tel", "telephone", "mobile", "cell", "cellphone", "טלפון", "נייד", "פלאפון", "סלולרי")
SUBJECT = _kw("subject", "topic", "נושא", "נושא הפנייה")
MESSAGE = _kw("message", "msg", "comment", "comments", "enquiry", "inquiry", "body", "content", "details",
              "your message", "הודעה", "תוכן", "פרטים", "הערות", "הערה", "פנייה", "פניה", "בקשה", "תוכן הפנייה")
COMPANY = _kw("company", "business", "organization", "organisation", "firm", "חברה", "עסק", "ארגון", "שם העסק",
              "שם החברה")
NAME = _kw("name", "full name", "fullname", "first name", "firstname", "fname", "last name", "lastname", "lname",
           "surname", "your name", "שם", "שם מלא", "שם פרטי", "שם משפחה")
NAME_FIRST = _kw("first", "fname", "firstname", "given", "פרטי")
NAME_LAST = _kw("last", "lname", "lastname", "surname", "family", "משפחה")
CONSENT = _kw("agree", "consent", "accept", "acceptance", "terms", "privacy", "policy", "gdpr", "מסכים", "מסכימה",
              "מאשר", "מאשרת", "אישור", "תקנון", "תנאי", "פרטיות", "מדיניות")

_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden|(left|top)\s*:\s*-\d{3,}px", re.I)
_TEXTLIKE = {"", "text", "email", "tel", "url", "number", "search"}
_IGNORED_TYPES = {"submit", "button", "image", "reset"}
_OK_ENCODINGS = {"application/x-www-form-urlencoded", "multipart/form-data"}


@dataclass
class MappedField:
    name: str
    role: str
    required: bool
    kind: str            # input type, "textarea" or "select"
    label: str = ""
    part: str | None = None   # for role name: "full", "first" or "last"
    value: str | None = None  # for checkboxes: the value sent when ticked


@dataclass
class FormPlan:
    form_url: str
    action_url: str
    method: str
    encoding: str
    fields: list[MappedField] = field(default_factory=list)
    hidden_fields: dict[str, str] = field(default_factory=dict)
    honeypots: list[str] = field(default_factory=list)
    ignored_optional: list[str] = field(default_factory=list)
    submit: tuple[str, str] | None = None

    def roles(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for f in self.fields:
            out.setdefault(f.role, []).append(f.name)
        return out

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [f"form page: {self.form_url}",
                 f"submits to: {self.action_url} ({self.method.upper()}, {self.encoding})"]
        for f in self.fields:
            extra = f", {f.part}" if f.part else ""
            lines.append(f"  fill {f.name!r} as {f.role}{extra}{' (required)' if f.required else ''}"
                         + (f"  [{f.label}]" if f.label else ""))
        if self.hidden_fields:
            lines.append(f"  keep hidden: {', '.join(self.hidden_fields)}")
        if self.honeypots:
            lines.append(f"  leave empty (honeypot): {', '.join(self.honeypots)}")
        if self.ignored_optional:
            lines.append(f"  leave empty (optional, unknown): {', '.join(self.ignored_optional)}")
        return "\n".join(lines)


@dataclass
class PlanResult:
    status: str
    plan: FormPlan | None
    detail: str = ""


def _root(tag: Tag) -> Tag:
    node = tag
    while node.parent is not None:
        node = node.parent
    return node


def _text(t: Tag | None) -> str:
    return " ".join(t.get_text(" ").split()) if t is not None else ""


def label_for(el: Tag) -> str:
    parts: list[str] = []
    root = _root(el)
    el_id = el.get("id")
    if el_id:
        lab = root.find("label", attrs={"for": el_id})
        if lab is not None:
            parts.append(_text(lab))
    wrap = el.find_parent("label")
    if wrap is not None:
        parts.append(_text(wrap))
    if el.get("aria-label"):
        parts.append(str(el["aria-label"]))
    for ref in str(el.get("aria-labelledby", "")).split():
        lab = root.find(id=ref)
        if lab is not None:
            parts.append(_text(lab))
    if el.get("title"):
        parts.append(str(el["title"]))
    return " ".join(dict.fromkeys(p for p in parts if p))


def _haystack(el: Tag, label: str) -> str:
    raw = " ".join(str(el.get(a, "")) for a in ("name", "id", "placeholder")) + " " + label
    return re.sub(r"[_\-\[\]\.:]+", " ", raw).lower()


def is_required(el: Tag, label: str) -> bool:
    if el.has_attr("required") or str(el.get("aria-required", "")).lower() == "true":
        return True
    classes = {c.lower() for c in el.get("class", [])}
    if classes & {"required", "wpcf7-validates-as-required", "is-required"}:
        return True
    return bool(re.search(r"\*|\(חובה\)|\brequired\b|שדה חובה", label, re.I))


def is_honeypot(el: Tag, form: Tag) -> bool:
    if str(el.get("tabindex", "")).strip() == "-1":
        return True
    node: Tag | None = el
    while node is not None and node is not form.parent:
        if node.has_attr("hidden") or str(node.get("aria-hidden", "")).lower() == "true":
            return True
        if _HIDDEN_STYLE.search(str(node.get("style", ""))):
            return True
        if any("honeypot" in c.lower() for c in node.get("class", [])):
            return True
        if node is form:
            break
        node = node.parent
    return False


def classify_field(el: Tag, label: str) -> tuple[str, str | None] | None:
    """Return (role, part) or None if the field cannot be classified."""
    tag = el.name
    typ = str(el.get("type", "")).lower() if tag == "input" else tag
    hay = _haystack(el, label)
    if typ == "checkbox":
        return ("consent", None) if CONSENT.search(hay) else None
    if typ in ("radio", "file", "select", "date", "password", "range", "color", "url", "number"):
        return None
    if typ == "email":
        return ("email", None)
    if typ == "tel":
        return ("phone", None)
    if tag == "textarea":
        return ("message", None)
    if COMPANY.search(hay):
        return None
    if EMAIL.search(hay):
        return ("email", None)
    if PHONE.search(hay):
        return ("phone", None)
    if SUBJECT.search(hay):
        return ("subject", None)
    if MESSAGE.search(hay):
        return ("message", None)
    if NAME.search(hay):
        part = "first" if NAME_FIRST.search(hay) else "last" if NAME_LAST.search(hay) else "full"
        return ("name", part)
    return None


def build_plan(form: Tag, page_url: str) -> PlanResult:
    method = str(form.get("method", "get")).strip().lower() or "get"
    encoding = str(form.get("enctype", "")).strip().lower() or "application/x-www-form-urlencoded"
    action = urljoin(page_url, str(form.get("action", "")).strip() or page_url)
    plan = FormPlan(form_url=page_url, action_url=action, method=method, encoding=encoding)

    a, p = urlsplit(action), urlsplit(page_url)
    if a.scheme not in ("http", "https"):
        return PlanResult(UNCLEAR, plan, f"form action is not an http(s) URL: {action}")
    if registrable_domain(a.hostname or "") != registrable_domain(p.hostname or ""):
        return PlanResult(UNCLEAR, plan, f"form submits to another domain: {a.hostname} (page is on {p.hostname})")
    if method != "post":
        return PlanResult(UNCLEAR, plan, f"form method is {method!r}, not post")
    if encoding not in _OK_ENCODINGS:
        return PlanResult(UNCLEAR, plan, f"unsupported form encoding {encoding!r}")

    unknown_required: list[str] = []
    for el in form.find_all(["input", "textarea", "select"]):
        name = el.get("name")
        typ = str(el.get("type", "")).lower() if el.name == "input" else el.name
        if el.name == "input" and typ in _IGNORED_TYPES:
            if typ == "submit" and name and plan.submit is None:
                plan.submit = (str(name), str(el.get("value", "")))
            continue
        if not name or el.has_attr("disabled"):
            continue
        name = str(name)
        if typ == "hidden":
            plan.hidden_fields[name] = str(el.get("value", ""))
            continue
        if el.name == "input" and typ in _TEXTLIKE and is_honeypot(el, form):
            plan.honeypots.append(name)
            continue
        label = label_for(el)
        required = is_required(el, label)
        role = classify_field(el, label)
        if role is None:
            if required:
                unknown_required.append(f"{name}" + (f" [{label}]" if label else ""))
            else:
                plan.ignored_optional.append(name)
            continue
        plan.fields.append(MappedField(name=name, role=role[0], required=required, kind=typ, label=label,
                                       part=role[1], value=str(el.get("value", "on")) if typ == "checkbox" else None))
    for btn in form.find_all("button"):
        if str(btn.get("type", "submit")).lower() == "submit" and btn.get("name") and plan.submit is None:
            plan.submit = (str(btn["name"]), str(btn.get("value", "")))

    if unknown_required:
        return PlanResult(UNCLEAR, plan, "required field(s) not recognized: " + "; ".join(unknown_required))
    if "message" not in plan.roles():
        return PlanResult(UNCLEAR, plan, "no field to put the message in")
    return PlanResult(READY, plan, "")
