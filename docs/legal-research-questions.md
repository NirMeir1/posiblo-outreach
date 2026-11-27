# Deep research brief: Israeli law for Posiblo's one-time consent-request outreach

## Goal of this research

This research has **two equal goals**:

1. **Answer every question** below with a clear verdict (see the rules below).
2. **Recommend the best legal way to reach the goal.** Posiblo **must** do this outreach. The question is **how** to do it legally, not **whether** to do it. Give a concrete, step-by-step plan that is legally safe and reaches as many businesses as possible. See section 5.

**Scope: Israel only.** Israeli law, an Israeli sender, and Israeli businesses as recipients. Don't research other countries' laws (GDPR, CAN-SPAM, etc.).

**The business goal:** get **written consent** from as many Israeli businesses as possible to receive information about Posiblo's automation and AI services. Then, legally, send information only to those who agreed.

**Today's reach** (dry-run on 188 business websites; nothing has been sent yet):

| Outcome | Share |
|---|---|
| Ready to send through the contact form | 17% |
| Blocked by CAPTCHA | 30% |
| The form has unknown required fields | 13% |
| No message box in the form | 14% |
| The form uses GET, not POST | 8% |
| No form found | 11% |
| Fetch or robots.txt errors | 6% |

Email to the address published on each website could reach many of the blocked sites. That's why the legal status of email matters so much.

For **every question below**, give a clear verdict:

- **OK**: clearly allowed. Cite the exact rule (statute section, regulation, official guideline, or court ruling).
- **GRAY**: no specific rule either way. Not clearly forbidden, but not clearly allowed. Say what the risk is and how courts or regulators have leaned, if at all.
- **NOT OK**: clearly forbidden. Cite the exact rule.

Rules for the research:

- **Use only reliable, official sources.** Good: Knesset legislation, Nevo law texts, gov.il (Ministry of Communications, Privacy Protection Authority, Ministry of Justice), and court rulings (the Supreme Court first, then district courts, then magistrate and small-claims courts). Law-firm blogs and vendor guides are not enough on their own. Use them only to find primary sources.
- **Quote the Hebrew wording** of the rule where it matters.
- **Give every source:** a URL, and for rulings the case number, court and date.
- **Separate binding precedent** (Supreme Court) **from non-binding rulings** (magistrate and small-claims courts).
- **Say "unknown"** when no source answers a question. Do not guess.
- **Use the newest law text.** Section 30A was last amended by amendment 76 (2022). The Privacy Protection Law changed with amendment 13, in force from August 2025.
- **Check for anything newer** (today is November 2026): any 2025–2026 amendment, bill, regulation or regulator guidance on spam, direct mail or scraping. For example, the Communications Law had amendment 83 in July 2026; check whether it touches section 30A.

---

## 1. What Posiblo plans to do

- Posiblo is run by one person (the owner) in Israel. It offers automation and AI services to businesses.
- An automatic tool reads a list of Israeli business websites (about 190 sites).
- For each business, the tool sends **one message only**. The message asks whether the business **agrees to receive information** from Posiblo. It does not advertise any offer. There is never a second message to the same business.
- **Channel 1 (built):** the tool submits the business's own **website contact form** ("צור קשר") automatically, filling in name, email, phone and the message.
- **Channel 2 (planned, not built):** where a site has no usable form, the tool sends **one email** to the address the business publishes on its own website.
- The tool never gets around CAPTCHAs, logins or access controls. It respects robots.txt. It skips sites that say they don't want solicitation ("אין לשלוח פרסומות" and similar).
- **The list of sites** was made by an AI assistant (Claude), which was simply asked to list websites of businesses in Israel. Nothing was bought, copied from a database, or taken from a private source. The list holds **website addresses only**: no names, emails or phone numbers. The tool takes contact details only from each business's own public website, at send time.
- If a business replies "הסר", its domain, email and phone go on a permanent "never contact" list.
- The tool keeps a local database (SQLite) and logs: the site address, form address, status, time, and the message version sent.

## 2. The message

**Current template (`templates/consent_request_v1.txt`), exactly as it would be sent:**

> פרסומת
> שלום, אני [שם הבעלים] מ-Posiblo. האם תרצו שאשלח אליכם מידע על שירותי אוטומציה ו-AI לעסקים? אם כן, השיבו "כן". אם לא, אין צורך לענות ולא אפנה שוב.
> פנייה בדיוור ישיר. הפרטים נלקחו מהאתר הציבורי של העסק. למחיקה מהרשימה השיבו "הסר".
> Posiblo, [כתובת], [טלפון], [כתובת מייל]

**Subject line** (used in email, or in a form's subject field if it has one): `פרסומת - בקשת הסכמה`

**Hebrew-only variant under consideration (a possible v2):** the same text with "Posiblo" → "פוסיבלו" and "AI" → "בינה מלאכותית".

---

## 3. What has already been verified (starting point; please re-check)

1. **Communications Law (Bezeq and Broadcasting) 1982, section 30A(ב)**, read in the current text on Nevo:
   - Advertising (דבר פרסומת) by fax, automatic dialing, electronic message or SMS needs the recipient's **prior explicit written consent**.
   - Last sentence of 30A(ב): *"פנייה חד-פעמית מטעם מפרסם לנמען שהוא בית עסק ... באחת הדרכים האמורות בסעיף קטן זה, המהווה הצעה להסכים לקבל דברי פרסומת מטעמו, לא תיחשב הפרה של הוראות סעיף זה."*
2. **"הודעה אלקטרונית"** is defined in 30A(א) as *"מסר בזק מקודד המועבר ברשת האינטרנט אל נמען או קבוצה של נמענים, וניתן לשמירה ולאחזור בדרך ממוחשבת"*.
3. **30A(ה), required details:**
   - The word "פרסומת" at the start of the message, and in the subject line of an electronic message.
   - The advertiser's name, address and contact details.
   - The right to refuse, and a valid internet address for refusing.
4. **30A(ד), refusal:** a refusal may be given in writing or in the same way the message was sent, as the recipient chooses.
5. **Penalties:**
   - 30A(י): up to **₪1,000 per message**, with no need to prove damage. 30A(י)(5) presumes the sender acted knowingly. There is no defense for sending after a refusal.
   - 30A(ו): criminal fines.
   - 30A(ח): the **manager of a corporation, and the person in charge of its marketing, are personally liable**.
6. **Bat Yam Magistrate's Court, 49111-10-22, Keinan v. Eshel Jerusalem, 2 August 2023** (non-binding):
   - A message that **already contains the advertising itself** is not a one-time consent request.
   - Refusal must be possible in the same channel the message was sent.
7. **Hadera Small Claims Court, 35387-09-11, Yigal Ram v. Geva Barat, 2011** (non-binding; only a summary was read):
   - The first approach to a business was lawful.
   - A **second approach without consent** was a violation.
8. **Privacy Protection Authority guideline 2/2017, updated after amendment 13** (gov.il PDF):
   - The spam law and the direct-mail rules can apply at the same time (section 14.3).
   - Every direct-mail message must state (section 19.1): that it is direct mail, the right to be deleted and where to ask, and the sender's identity, address and data sources.
   - Deletion requests: within 30 days.
   - Database registration is required only where the database's main purpose is passing data to others (including direct-mail services) and it holds more than 10,000 people (section 15).
   - Fine for leaving out the direct-mail details: ₪50 per recipient.
   - Section 5: the opt-out model is valid only if adding the person to the database was not itself a violation of the law.
9. **No Supreme Court ruling** on the one-time business exception was found. Please search again.
10. **Could not be read** (gov.il refused automated access with a 403); please read these:
    - The Ministry of Communications spam FAQ: https://www.gov.il/he/departments/faq/17052018_7
    - The Privacy Protection Authority page "גם כתובות דואר אלקטרוני הן מידע אישי": https://www.gov.il/he/pages/database_mails_and_names

---

## 4. Questions (give OK / GRAY / NOT OK for each)

### A. Is the plan allowed at all?

- **A1.** Does the plan (one message per business, by contact form or email) fall under the **one-time business exception** in section 30A(ב)?
- **A2.** Is a message submitted through a business's **website contact form** an "הודעה אלקטרונית" under 30A(א)? Is there a ruling on contact forms specifically? If a form is **not** an electronic message, does section 30A apply to it at all?
- **A3.** Who counts as a **"בית עסק"**? Is there a definition or a court test? Specifically:
  - a sole proprietor (עוסק פטור / מורשה) or a freelancer
  - a one-person clinic (doctor, therapist, lawyer, accountant)
  - a nonprofit (עמותה)
  - a business that uses a personal Gmail address
  - a business page on a platform (Facebook, Wix)
- **A4.** Does **"חד-פעמית"** mean one approach per business **across all channels together** (form, email, SMS, phone)? Or one per channel?
- **A5.** If a form submission's result is **unclear** (the tool can't confirm it arrived), may the business be emailed too? Or does that count as a second approach?
- **A6.** One business may have **several websites, emails or branches**. Is that one "recipient" or several?
- **A7.** Does sending **automatically, by software**, change anything legally compared to a person typing the same message?
- **A8.** Many Israeli businesses use a foreign domain (.com) or a website hosted abroad. Does Israeli law apply the same way to them?

### B. The message text

- **B1.** Is the text a **pure consent request**, even though it names the field ("אוטומציה ו-AI לעסקים")? Where is the line between "offering to agree to receive ads" and "containing an ad"? (Compare the Bat Yam ruling.)
- **B2.** Does the consent request **itself** have to meet the 30A(ה) details (the word "פרסומת", name, address, a way to refuse)? Or does the exception free it from them?
- **B3.** Does the text meet **all** the required details of **30A(ה)** and of **section 17ו(א) of the Privacy Protection Law**? What is missing?
- **B4.** **Whose name and address** must appear: the brand "Posiblo", or the owner's own name? Is a business address required, or is a home address enough? Is a P.O. box enough?
- **B5.** Must the advertiser be a **registered business** (עוסק / company) to send this?
- **B6.** **Personal liability:** does it matter (30A(ח)) whether Posiblo is a sole proprietorship or a company?
- **B7.** In a **contact form**, where must "פרסומת" appear, given that forms have no "subject line" unless there is a subject field? Is it enough at the start of the message body?
- **B8.** Is "**השיבו 'הסר'**" a valid way to refuse in **each channel**?
  - Email: the recipient can reply directly.
  - Contact form: the recipient cannot reply through their own form, only to the email address written in the message. Is that "the same way the message was sent" (30A(ד), and the Bat Yam ruling)?
- **B9.** Is the sentence "**הפרטים נלקחו מהאתר הציבורי של העסק**" enough as the "source of the data" under 17ו(א)?
- **B10.** Are "Posiblo" and "AI" in English a problem? Does a Hebrew-only version (v2) change anything legally?

### C. Collecting the details

- **C1.** May the tool collect a business's **email address or contact form from its own public website** and use it for this one message? Is that lawful under the Privacy Protection Law?
- **C2.** Is a business's email address **"מידע אישי"** (personal data)? Does that depend on whether it is a generic address (info@) or a person's (dana@, or a sole proprietor's Gmail)?
- **C3.** Is the tool's list (domain, form address, status, time) a **"מאגר מידע"** (database) under the Privacy Protection Law after amendment 13? Does it need **registration** or a **notice** to the Privacy Protection Authority?
- **C4.** Do the **Data Security Regulations 2017** (תקנות הגנת הפרטיות (אבטחת מידע)) apply to this list and the logs? Which security level, and what is required?
- **C5.** Is the **source of the list** lawful? The list of website addresses was made by an AI assistant asked to list Israeli business websites, and contact details are then read from each business's own public site.
  - Is this a lawful source?
  - Must the message state the source more precisely than "הפרטים נלקחו מהאתר הציבורי של העסק"?
  - For comparison, how would the answer differ if the list were bought, taken from a business directory, from search results, or from a public registry?
- **C6.** Some websites' **terms of use** forbid commercial use of their contact form, or automated access. Is breaking such terms a legal problem (contract, the Computers Law 1995, trespass)?
- **C7.** Is **automated access to public web pages** (scraping), while respecting robots.txt, lawful under the **Computers Law 1995**, the Privacy Protection Law, or the Privacy Authority's positions on scraping?
- **C8.** Some forms have a **required checkbox** accepting the site's terms or privacy policy. May the tool tick it automatically for us? What do we legally agree to by ticking it?
- **C9.** If a site states "**no solicitation**" or "אין לשלוח פרסומות", is that legally a **refusal** (הודעת סירוב) under 30A(ד)? (The tool already skips such sites.)

### D. After sending

- **D1.** If a business answers "**כן**", is that reply valid "prior explicit written consent" under 30A(ב) for **future ads**? Does the person replying need authority to act for the business?
- **D2.** **Proof of consent:** what records must be kept, in what form, and for how long?
- **D3.** Does consent **expire**? For how long is a "כן" valid?
- **D4.** If a business answers "**הסר**":
  - May its domain, email or phone stay on a **permanent "never contact" list**?
  - Or does that conflict with the **right to deletion** under section 17ו(ב) of the Privacy Protection Law?
- **D5.** **Deadlines** for handling "הסר": 30 days under the Privacy Protection Law (17ו(ה)). Is there a deadline under 30A as well?
- **D6.** If there is **no answer**, may the business ever be approached again: after a year, by another channel, or about another topic?
- **D7.** **Retention:** how long may the ledger, logs and backups be kept?

### E. Risk and enforcement

- **E1.** What are the **real-world damages** courts award per message under 30A(י) in cases like this (business recipients, one message)? Give example rulings and amounts.
- **E2.** Are **class actions** (תובענות ייצוגיות) under the spam law possible for one message per recipient sent to many businesses?
- **E3.** What are the **criminal fine amounts** under 30A(ו), as referenced from the Penal Law section 61(א)(3) and (4)?
- **E4.** What should be done on receiving a **demand letter** (מכתב התראה) or a claim?
- **E5.** What **defenses** exist? Are there rulings where a one-time business consent request was found lawful, and what made it lawful?

### F. Other channels (for comparison)

- **F1.** **SMS** to a business's published mobile number: is the one-time business exception the same as for email?
- **F2.** **WhatsApp** messages: are they "הודעה אלקטרונית" or "הודעת מסר קצר"? Same exception?
- **F3.** **Phone calls by a person** (not automatic dialing): does 30A apply? Does the "אל תתקשר אליי" (do-not-call) registry apply to businesses?
- **F4.** **LinkedIn** or other social media messages to a business page: does 30A apply?

---

## 5. The recommended approach (the "how")

Beyond the answers, tell Posiblo **what to do**. Cover all of these:

- **G1. The best overall approach.** Which channel or channels to use (contact form, email, SMS, WhatsApp, phone, LinkedIn, or a mix), in what order, and why. Rank them by legal safety **and** by reach.
- **G2. A message text that is clearly OK.** Propose an exact Hebrew text (a v2) that is clearly a pure consent request and contains every required detail. Explain each line. Give separate versions for form and email if they need to differ.
- **G3. The exact consent flow:**
  - first message → the "כן" reply → how to record proof → when and what may be sent next
  - the "הסר" reply → what to do, and by when
  - no reply → what is allowed later, if anything
- **G4. A compliance checklist** to run before every send: the business check, the one-time check across channels, the required details, the refusal path, records.
- **G5. What to set up first:**
  - business registration (sole proprietor or company)
  - the address to show in the message
  - database registration or notice, if needed
  - data security steps
  - a privacy notice
  - retention rules
- **G6. How to reach more businesses legally.** For each blocked group in the table above (CAPTCHA, unknown fields, no message box, no form), what is the legal way to reach it, if any.
- **G7. What to avoid.** The practices that are NOT OK, or too risky in GRAY, with a safer alternative for each.
- **G8. How to reduce the risk that is left:** a cap on volume, a pilot batch, insurance, a demand-letter response template, and anything else that helps.
- **G9. Things only a lawyer can decide.** List them, each with one precise yes/no question, so a lawyer consultation is short.

## 6. Output wanted

1. **The recommended plan first:** a short, step-by-step answer to G1–G9 that Posiblo can follow.
2. **One table:** question ID | verdict (OK / GRAY / NOT OK / UNKNOWN) | one-line reason | main source.
3. **Then, per question:** a short explanation, the exact rule (quoted in Hebrew where relevant), and the sources.
4. **A short list of the GRAY and NOT OK items** that most affect the plan, and what change to the plan would make each one OK.
5. **A list of every source used**, with URLs.
