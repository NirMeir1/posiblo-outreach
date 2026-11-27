# Message content of the one-time consent request, and the consent flow after it (Israel, as of 27 Nov 2026)

Scope: questions B1–B10, D1–D3, D5–D6 of `docs/legal-research-questions.md`, plus a recommended Hebrew v2 text and consent flow (G2/G3).

How much weight each source carries (read this first):
- **Binding (Supreme Court judgment, 3 justices):** רע"א 1954/14 אילן חזני נ' שמעון הנגבי (סיתונית מועדון דאייה ורחיפה במצנחים), 4.8.2014, main opinion by Justice ע' פוגלמן. The brief calls it "חזני נ' שמשון". That name is wrong: the respondent is שמעון הנגבי. Full text: [law.haifa.ac.il PDF](https://law.haifa.ac.il/wp-content/uploads/2019/01/14019540.M05.pdf).
- **Supreme Court, but persuasive only:** רע"א 1231/17 ישי רז נ' אימפרשן מדיה בע"מ, decision of Deputy President א' רובינשטיין sitting alone, 20.4.2017. Leave to appeal was denied, and the remarks on consent are framed "לכאורה" (prima facie). [law.co.il PDF](https://www.law.co.il/media/computer-law/raz3.pdf).
- **Non-binding:**
  - Bat Yam Magistrate's Court (Senior Registrar), תאד"מ 49111-10-22 קינן נ' אשל ירושלים, 2.8.2023 ([law.co.il PDF](https://www.law.co.il/media/computer-law/keinan8.pdf)).
  - Hadera Small Claims, ת"ק 35387-09-11 יגאל רם נ' גבע באראט בע"מ, 2011 ([law.co.il summary](https://www.law.co.il/computer-law/2011/12/19/igaal-ram-v-geva-barat-ltd/)). The ruling PDF is a scanned image, so its text could not be extracted, and only the summary was read.
  - Tel Aviv Small Claims, אביהב נ' מיפרייס בע"מ, given כ"ג טבת תשע"ז ([isoc.org.il PDF](https://www.isoc.org.il/files/spam/verdict/553.pdf)). The case number and digits are garbled in the extracted text.
- **Legislative history (an aid to interpretation, not binding):** joint Economics + Science committee protocol No. 3, 27.11.2007, on the bill that became amendment 40 ([Knesset .doc](https://fs.knesset.gov.il/17/Committees/17_ptv_134779.doc)).
- **Statute:**
  - Communications Law s.30A, current consolidated Nevo text (saved copy used, `law-dl/s30a.txt`; Nevo page [nevo.co.il law01/032_002](https://www.nevo.co.il/law_html/law01/032_002.htm)). Amendment 40 as published in Sefer HaHukim ([Knesset PDF](https://fs.knesset.gov.il//17/law/17_lsr_299991.pdf)).
  - Privacy Protection Law s.17ו (pre-amendment-13 consolidated text at [TAU PDF](https://law.tau.ac.il/sites/law.tau.ac.il/files/law_lgbt/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_0.pdf)), plus the amendment 13 text ([gov.il PDF](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)).
  - Privacy Protection Authority guideline 2/2017, updated after amendment 13 (local extract used; an older gov.il copy is at [gov.il direct mail PDF](https://www.gov.il/blobFolder/policy/direct_mail_2/he/direct%20mail.pdf)).
- **Not readable:** the Ministry of Communications spam FAQ returned HTTP 403 at both URLs tried ([faq/17052018_7](https://www.gov.il/he/departments/faq/17052018_7), [pages/17052018_7](https://www.gov.il/he/pages/17052018_7)). I did not try to get around the block.

---

## B1. Is the text a "pure consent request" even though it names the field ("אוטומציה ו-AI לעסקים")? Where is the line?

### Takeaway
**GRAY, leaning OK.** The binding test (Chazani, Supreme Court 2014) is that the one-time request must be a **"neutral" offer that carries no advertising of the product or service itself**. Naming only the category of ads you are asking consent for, with no benefits, prices, offer, links or call to buy, fits that test better than any ruling where the request failed. No ruling was found that holds a message like the current one lawful or unlawful.

### Cited Findings
- Statute, s.30A(ב), last sentence: "פנייה חד-פעמית מטעם מפרסם לנמען שהוא בית עסק ... באחת הדרכים האמורות בסעיף קטן זה, המהווה הצעה להסכים לקבל דברי פרסומת מטעמו, לא תיחשב הפרה של הוראות סעיף זה." — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- Definition, s.30A(א): "דבר פרסומת" – "(1) מסר המופץ באופן מסחרי, שמטרתו לעודד רכישת מוצר או שירות או לעודד הוצאת כספים בדרך אחרת" — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- **Binding rule (Chazani, para 16):** "ברם פנייה הכוללת כשלעצמה דבר פרסומת אינה יכולה להיחשב פנייה מהסוג המותר בסעיף. אם לא נאמר כך, נימצא מאפשרים לכל מפרסם לשלוח הודעת פרסומת אחת שמשולבת בה גם הצעה לקבל דברי פרסומת בעתיד. פרשנות זו עומדת בניגוד לתכלית החוק. ההצעה שסעיף 30א(ב) סיפה מדבר בה היא הצעה "ניטראלית" שלא כרוכה בה פרסומת של המוצר או השירות שהשולח מבקש לפרסם." — [רע"א 1954/14 חזני נ' הנגבי, 4.8.2014](https://law.haifa.ac.il/wp-content/uploads/2019/01/14019540.M05.pdf)
- **What failed in Chazani:**
  - The emails had the subject "הזמנה להתנסות בחוויית רחיפה – חינם (פרסומת)".
  - Each one carried the footer "המייל נשלח על פי החוק החדש לרשימה עסקית באופן חד פעמי. אם קיבלתם מייל זה בטעות אתכם הסליחה, במידה ואינך מעוניין להמשיך ולקבל מחברתנו או מטעמה דברי פרסומת, נא...".
  - The court held the sender breached the law for every message, because the email was itself an ad (a free-trial invitation). Calling it "one-time to a business list" did not help. Paras 12–16 — [Chazani](https://law.haifa.ac.il/wp-content/uploads/2019/01/14019540.M05.pdf)
- Chazani also says that what counts as a "בית עסק" was not decided, and the court only assumed it for argument: "השאלה מהו ייחשב לבית עסק לצורך כך לא נדונה בערכאות הקודמות, ולצורך הדיון אניח..." — [Chazani para 16](https://law.haifa.ac.il/wp-content/uploads/2019/01/14019540.M05.pdf)
- **Non-binding, Bat Yam (paras 19–32):**
  - Donation-request SMSs ("הצטרפו אלינו ונסייע להם במזון...", "תנו עכשיו מתנות לאביונים...") carried a link to a landing page with donation amounts.
  - The court held: "פנייה שכוללת את דבר הפרסומת בתוכה אינה נחשבת פנייה חד פעמית ... המהווה הצעה להסכים לקבל את דברי הפרסומת" (para 32).
  - It relied partly on the landing page reached through the link (paras 24–27). — [Bat Yam 49111-10-22](https://www.law.co.il/media/computer-law/keinan8.pdf)
- **Legislative history:** in committee, the Knesset legal adviser (אתי בנדלר) described the exception as "פנייה לבית עסק, והשאלה היא האם הוא מסכים לקבל דברי פרסומת, **בלי הפרסומת עצמה**. כתוב כאן: 'המהווה הצעה להסכים לקבלת דברי פרסומת מטעמו'". — [Knesset joint committee protocol 3, 27.11.2007](https://fs.knesset.gov.il/17/Committees/17_ptv_134779.doc)
- In the same session, speakers proposed that the one-time approach be limited to matters "הנוגעים למהותו של בית העסק" and to "כתובת אחת ויחידה של אותו בית עסק". **Neither limit appears in the enacted text.** — [same protocol](https://fs.knesset.gov.il/17/Committees/17_ptv_134779.doc); compare the enacted text in [amendment 40, Sefer HaHukim](https://fs.knesset.gov.il//17/law/17_lsr_299991.pdf)
- **Non-binding, Hadera (2011), summary only:** a first approach (by fax) to a business was held lawful as a one-time consent offer, and a second approach without proven consent was unlawful. The summary does not describe what the first fax said. ₪800 was awarded. — [law.co.il summary of ת"ק 35387-09-11](https://www.law.co.il/computer-law/2011/12/19/igaal-ram-v-geva-barat-ltd/)

### Inferences
- A consent request has to say **what** the recipient would agree to receive. Otherwise the consent would not be "מפורשת" or meaningful. Naming the field ("שירותי אוטומציה ובינה מלאכותית לעסקים") is the smallest description that does this, and is not by itself "encouraging purchase".
- Where the line falls, judging from the rulings found:
  - **Over the line:** a free offer or trial (Chazani), a call to act or donate (Bat Yam), a link to a sales or landing page (Bat Yam paras 24–27).
  - **Also risky, by inference:** benefit claims ("לחסוך זמן", "להגדיל מכירות"), prices or discounts.
  - **Safe side:** a bare question whether the recipient agrees to receive ads on a named topic.
- The current v1 text has no benefits, prices, offer or links. Its weak points are elsewhere (see B3 and B8).
- Do not include a link to Posiblo's website. Bat Yam used the linked landing page as evidence that the message was an ad.

### Gaps
- No ruling was found, at any level, that holds a specific bare "may I send you information about X?" message to a business lawful or unlawful.
- The Hadera ruling's text is a scanned image and could not be read, so what its lawful first fax said is unknown.
- The Ministry of Communications FAQ could not be read (HTTP 403).

---

## B2. Must the one-time consent request itself carry the 30A(ה) details?

### Takeaway
**UNKNOWN (no ruling found); treat as required.** Read literally, 30A(ה) binds a "מפרסם המשגר דבר פרסומת", and the exception says a neutral request "לא תיחשב הפרה של הוראות **סעיף** זה" (the whole section). Both points support an argument that a neutral request is exempt. No court or regulator has said so. Missing labels are cheap to add and expensive to get wrong, so include every detail.

### Cited Findings
- s.30A(ה)(1): "מפרסם המשגר דבר פרסומת בהתאם להוראות סעיף זה יציין בו את הפרטים האלה באופן בולט וברור, שאין בו כדי להטעות:
  (א) היותו דבר פרסומת; המילים "פרסומת" ... יופיעו בתחילת דבר הפרסומת, ואם דבר הפרסומת משוגר באמצעות הודעה אלקטרונית – בכותרת ההודעה;
  (ב) שמו של המפרסם, כתובתו ודרכי יצירת הקשר עמו;
  (ג)(1) זכותו של הנמען לשלוח, בכל עת, הודעת סירוב כאמור בסעיף קטן (ד), ודרך אפשרית למשלוח הודעה כאמור שהיא פשוטה וסבירה בנסיבות העניין, ואם דבר הפרסומת משוגר באמצעות הודעה אלקטרונית – כתובת תקפה של המפרסם ברשת האינטרנט לצורך מתן הודעת סירוב". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- The exception text: "...לא תיחשב הפרה של הוראות סעיף זה" (section, not subsection). — [Nevo s.30A(ב)](https://www.nevo.co.il/law_html/law01/032_002.htm)
- Penalties for missing details:
  - s.30A(ו)(2): a criminal fine under Penal Law 61(א)(3) for an ad "שלא צוינו בו הפרטים האמורים בסעיף קטן (ה)". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
  - Raz (Supreme Court decision, 2017): a small claims court awarded ₪10,000 for 122 emails "שבהן לא צוינה בראשיתן המלה "פרסומת"" even though consent had been found. The Supreme Court left the amount in place and called it "גבוה בנסיבות הענין". — [רע"א 1231/17 רז נ' אימפרשן מדיה](https://www.law.co.il/media/computer-law/raz3.pdf)
- No regulations under 30A(יא) were found. That subsection would let the minister set "אופן ציון הפרטים שיש לציין בדבר פרסומת" and "פרטים נוספים". — [Nevo s.30A(יא)](https://www.nevo.co.il/law_html/law01/032_002.htm); searches found none (see D3).

### Inferences
- If a court found the request was **not** a neutral offer, it would be an ordinary ad. It would then breach 30A(ב) (no consent) and probably 30A(ה) too. Full labelling at least removes the second breach.
- Labelling a neutral request "פרסומת" does not by itself turn it into an ad. The label is a statutory formality. This is an inference; no source was found on the point.

### Gaps
- No ruling or regulator guidance on whether 30A(ה) applies to the one-time consent request.

---

## B3. Does the current v1 text meet 30A(ה) and Privacy Protection Law 17ו(א)? What is missing?

### Takeaway
**NOT OK as written. It is fixable.**
- **Missing or weak under 30A(ה):**
  - The address and contact details are still placeholders.
  - The message never states the **right to refuse "בכל עת"**.
  - It gives no explicit **valid internet address for refusal**: "השיבו 'הסר'" does not say where to reply, and in a contact form there is nothing to reply to.
  - The advertiser's legal name is not given (see B4).
- **17ו(א) (applies only where the recipient is an individual, see below):**
  - "פנייה בדיוור ישיר" is present.
  - The deletion right is only implied, and no address for deletion requests is given.
  - The data source is incomplete (see B9).

### Cited Findings
- **Check against 30A(ה)** ([Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)):
  - (ה)(1)(א) "פרסומת" at the start: present (line 1). The email subject "פרסומת - בקשת הסכמה" is present.
  - (ה)(1)(ב) "שמו של המפרסם, כתובתו ודרכי יצירת הקשר עמו": "Posiblo, [כתובת], [טלפון], [כתובת מייל]" is all placeholders. Also see B4: a brand alone may not be "the advertiser's name".
  - (ה)(1)(ג)(1) "זכותו של הנמען לשלוח, **בכל עת**, הודעת סירוב" plus "דרך ... פשוטה וסבירה" plus, for an electronic message, "כתובת תקפה של המפרסם ברשת האינטרנט לצורך מתן הודעת סירוב": v1 says only "למחיקה מהרשימה השיבו 'הסר'". The right "at any time" is not stated, and no internet address is named.
- **Privacy Protection Law 17ו(א) wording:** "כל פניה בדיוור ישיר תכיל באופן ברור ובולט –
  (1) ציון כי הפניה היא בדיוור ישיר, בצירוף ציון מספר הרישום של המאגר המשמש לשירותי דיוור ישיר ...;
  (2) הודעה על זכותו של מקבל הפניה להימחק מן המאגר כאמור בסעיף קטן (ב), בצירוף המען שאליו יש לפנות לצורך כך;
  (3) זהותו ומענו של בעל [השליטה ב]מאגר המידע שבו מצוי המידע שעל פיו בוצעה הפניה, והמקורות שמהם קיבל ... מידע זה."
  — [pre-amendment-13 text, TAU PDF](https://law.tau.ac.il/sites/law.tau.ac.il/files/law_lgbt/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_0.pdf). Amendment 13 replaced "בעל מאגר" with "בעל שליטה במאגר" throughout — [amendment 13, s.1](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- PPA guideline 2/2017, s.19.1.1: where the approach is not based on data from a direct-mail-services database, "אין חובה לציין את מספר רישום המאגר, אלא רק את זהות השולח והמקורות". — PPA guideline 2/2017 (updated after amendment 13), local extract; [older gov.il copy](https://www.gov.il/blobFolder/policy/direct_mail_2/he/direct%20mail.pdf)
- **17ו may not apply to companies:**
  - In the Privacy Protection Law, "אדם" means "למעט תאגיד" for listed sections, and the list includes 17ו ([TAU text, s.3](https://law.tau.ac.il/sites/law.tau.ac.il/files/law_lgbt/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_0.pdf)).
  - Amendment 13 kept 17ו in that list and extended it to the definition "דיוור ישיר": "ואחרי "25" יבוא "וכן לעניין ההגדרות "דיוור ישיר", "מאגר מידע" ... "מידע אישי"..." — [amendment 13, s.2(2)](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- "דיוור ישיר" is defined as "פניה אישית לאדם, בהתבסס על השתייכותו לקבוצת אוכלוסין, שנקבעה על פי איפיון אחד או יותר של בני אדם ששמותיהם כלולים במאגר מידע". — [TAU text, s.17ג](https://law.tau.ac.il/sites/law.tau.ac.il/files/law_lgbt/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_0.pdf)
- PPA fine for an approach that breaches 17ו(א): ₪50 multiplied by the number of people approached (s.23כו(ג)(1)(ב)). — PPA guideline 2/2017 s.21.3 (local extract)

### Inferences
- A message to a company (בע"מ) is probably **not** "דיוור ישיר" to an "אדם", so 17ו(א) would not apply to it. A message to a sole proprietor, freelancer, clinic, or a named person's mailbox probably **is**.
- The tool cannot reliably tell these apart, so every message should carry the 17ו(א) details.

### Gaps
- No ruling found on whether a one-time consent request is "דיוור ישיר".
- No ruling found on whether a business's generic address (info@) is an "אדם" recipient.
- I did not read a post-amendment-13 consolidated text of 17ו itself. The amendment text I read changes 17ו only through the global word replacements.

---

## B4. Whose name and address must appear (brand vs owner; business vs home vs P.O. box)?

### Takeaway
**Name: GRAY, so use the legal name plus the brand. Address: UNKNOWN whether a P.O. box is enough.** The statute requires "**שמו של המפרסם**, כתובתו ודרכי יצירת הקשר עמו", shown "באופן בולט וברור, שאין בו כדי להטעות". For a sole proprietor, the advertiser is the person, so the owner's full legal name should appear next to the brand. No source defines "כתובתו".

### Cited Findings
- s.30A(ה)(1)(ב): "שמו של המפרסם, כתובתו ודרכי יצירת הקשר עמו", shown "באופן בולט וברור, שאין בו כדי להטעות". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- "מפרסם" is defined as "מי ששמו או מענו מופיעים בדבר הפרסומת כמען להתקשרות ... מי שתוכנו של דבר הפרסומת עשוי לפרסם את עסקיו או לקדם את מטרותיו...". — [Nevo s.30A(א)](https://www.nevo.co.il/law_html/law01/032_002.htm)
- Privacy 17ו(א)(3): "זהותו ומענו" of the controller. — [TAU text](https://law.tau.ac.il/sites/law.tau.ac.il/files/law_lgbt/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_0.pdf)
- In Avihav, the claimant complained that the sender's name and address were missing, "מה שנטען כי גרם לתובע טרחה רבה באיתורה". The court found these were breaches in the messages exhibited, though of low weight for damages. — [Avihav v. MyPrice (small claims, non-binding)](https://www.isoc.org.il/files/spam/verdict/553.pdf)

### Inferences
- "Posiblo" is not a legal person if the business is a sole proprietorship. A full legal name ("[שם מלא], פוסיבלו (Posiblo)") lets a recipient identify and sue the advertiser. That is the purpose courts read into the requirement, as Avihav's complaint about the "trouble locating" the sender shows.
- No rule bars a home address, and none requiring a business address was found. A street address where mail is received is safest. A P.O. box alone carries a risk that a court sees it as not "כתובתו". That is an inference, not a source.

### Gaps
- No ruling or guidance on P.O. boxes or home addresses under 30A(ה)(1)(ב). Whether a company number or עוסק number is needed: none required by the text.

---

## B5. Must the sender be a registered business to send this?

### Takeaway
**OK under 30A.** Section 30A has no requirement that the "מפרסם" be a registered business. The exception is "מטעם מפרסם", which is any advertiser. Whether tax law requires registration before trading was not researched and is out of scope.

### Cited Findings
- The definition of "מפרסם" and the exception wording in 30A(א) and (ב) contain no registration condition. — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)

### Inferences
- Registration matters indirectly: it decides **who** the advertiser is (person or company) and which address and name to show (B4, B6).

### Gaps
- Tax and VAT registration duties (פקודת מס הכנסה, חוק מע"מ) were not researched.

---

## B6. Does sole proprietor vs company affect personal liability (30A(ח))?

### Takeaway
**A company gives only limited protection.**
- **Sole proprietor:** the owner is the "מפרסם" and is directly liable, civilly (30A(ט)–(י), up to ₪1,000 per message) and criminally (30A(ו)).
- **Company:** the company is the advertiser. Its manager and marketing officer have a criminal supervision duty with a presumption of breach (30A(ח)). One non-binding ruling also held managers civilly liable together with the corporation.

### Cited Findings
- s.30A(ח): "מנהל של תאגיד וכן מי שאחראי לתחומי השיווק או הפרסום בתאגיד ... חייב לפקח ולעשות כל שניתן למניעת עבירה לפי סעיף קטן (ו) ...; המפר הוראה זו, דינו – קנס כאמור בסעיף 61(א)(3) לחוק העונשין; נעברה עבירה בידי התאגיד ... חזקה היא כי נושא משרה בתאגיד הפר את חובתו ... אלא אם כן עשה כל שניתן". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- Bat Yam (paras 35–37, 44): committee members of an amuta were held to be its managers under the Amutot Law ss.19 and 25, "ולכן נושאים באחריות לפעולות הנתבעת לפי חוק התקשורת". They had to pay ₪6,000 "ביחד ולחוד" with the amuta. — [Bat Yam 49111-10-22](https://www.law.co.il/media/computer-law/keinan8.pdf)

### Inferences
- With one owner running the tool, the owner would be "מנהל" and "אחראי לתחומי השיווק" in a company too. So incorporation does not remove personal exposure. It mainly changes whose name is on the claim.
- 30A(ח) on its face is a **criminal** supervision duty. Bat Yam extended personal liability to civil damages with little analysis. That point is for a lawyer.

### Gaps
- No Supreme Court ruling found on whether 30A(ח) creates civil personal liability.

---

## B7. In a contact form (no subject line), where must "פרסומת" appear?

### Takeaway
**GRAY (no ruling on contact forms found).** The statute requires "פרסומת" "בתחילת דבר הפרסומת", and for an electronic message also "בכותרת ההודעה". In a form, put it as the **first word of the message body**, and at the **start of the subject field when the form has one**. The email the website generates for the business has a subject set by the site, which the sender cannot control.

### Cited Findings
- s.30A(ה)(1)(א) (quoted in B2). — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- Courts do enforce the subject-line requirement. In Raz, ₪10,000 was awarded where "פרסומת" was missing from the opening of the messages. — [רע"א 1231/17](https://www.law.co.il/media/computer-law/raz3.pdf). Avihav found the missing "פרסומת" title to be a breach (non-binding). — [Avihav](https://www.isoc.org.il/files/spam/verdict/553.pdf)

### Inferences
- Whether a form submission is an "הודעה אלקטרונית" at all is question A2 (another researcher's scope). If it is not, the subject-line rule may not apply. If it is, a court could hold the sender to the subject requirement even though the sender cannot control the site's email subject.
- Mitigations within the sender's control:
  - "פרסומת" as the first word of the body (as v1 already does).
  - "פרסומת" at the start of any subject or topic field.
  - Possibly choose a "נושא/סיבת פנייה" dropdown value that best matches.
- Do not put "פרסומת" inside the name field. A name field should hold a true name, and the statute forbids misleading details. This is an inference.

### Gaps
- No ruling or guidance on labelling ads sent through website contact forms.

---

## B8. Is "reply 'הסר'" a valid refusal path in each channel?

### Takeaway
- **Email: OK in substance, but the wording should be fixed.** Replying to the same email is refusal "בדרך שבה שוגר"; still state the right "בכל עת" and give the email address explicitly.
- **Contact form: GRAY.** The recipient cannot answer through their own form. The message must give an explicit, simple refusal address (the sender's email) and ideally a second route. "השיבו 'הסר'" with no address is not enough.
- The non-binding Bat Yam ruling (para 34) reads the law as requiring that refusal be possible "באותה הדרך שבה שוגר דבר הפרסומת", but its reasoning is very short.

### Cited Findings
- s.30A(ד)(1): "הודעת הסירוב לא תהיה כרוכה בתשלום, למעט עלות משלוח ההודעה; הודעת הסירוב תינתן **בכתב או בדרך שבה שוגר דבר הפרסומת, לפי בחירת הנמען**". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- s.30A(ה)(1)(ג)(1): a "דרך אפשרית ... פשוטה וסבירה בנסיבות העניין", and for an electronic message "כתובת תקפה של המפרסם ברשת האינטרנט לצורך מתן הודעת סירוב". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- Bat Yam para 33–34:
  - The defendants offered removal "באמצעות משלוח הודעה הכוללת את הספרה "1" למספר: 052-…".
  - Court: "אפשרות זו אינה עולה בקנה אחד עם הוראות החוק. לפי סעיף 30א לחוק התקשורת, על הנתבעים לתת לנמען הזדמנות להודיע על סירובו לקבל את דברי הפרסומת באותה הדרך שבה שוגר דבר הפרסומת."
  - The ruling does not explain why an SMS to a phone number was not "the same way" for an SMS campaign. — [Bat Yam 49111-10-22](https://www.law.co.il/media/computer-law/keinan8.pdf)
- Avihav: the claimant argued he should be able to refuse "על ידי שליחת הודעת דוא"ל "הסר", ולא על ידי לחיצה על לינק היכולה, לטענתו, לסכן אותו בווירוסים". The court treated the missing same-channel removal option as one of the format breaches proven for part of the messages (non-binding). — [Avihav](https://www.isoc.org.il/files/spam/verdict/553.pdf)
- Chazani (binding) on removal options: a recipient has no duty to mitigate by asking for removal, but a removal option in the message can lower the damages (para 17, citing רע"א 2904/14 גלסברג נ' קלאב רמון). — [Chazani](https://law.haifa.ac.il/wp-content/uploads/2019/01/14019540.M05.pdf)

### Inferences
- Under 30A(ד)(1) the choice of written or same channel is the **recipient's** right. The sender's duty under (ה)(1)(ג)(1) is to state that right and to give a simple route plus a valid internet address.
- An email address is the most natural "internet address" for a written refusal. A removal-only web page URL is a second option that answers the "valid internet address" wording literally. This is an inference; no ruling was found on whether an email address alone satisfies "כתובת תקפה ... ברשת האינטרנט".
- For contact forms, give at least two routes:
  - "send 'הסר' to [email]" (written, simple);
  - "or call or send SMS to [phone]".
  An optional removal page on Posiblo's site would be a third. It must contain nothing but the removal function, so that it cannot be read as a landing page (compare Bat Yam paras 24–27). It would also conflict with project hard rule 9 (no links beyond the template) unless it is written into the template itself.
- Whatever channel a refusal comes through, honour it. 30A(י)(5)(א) removes all defence for any later message.

### Gaps
- No ruling on refusal routes for messages sent through a contact form.
- The reasoning in Bat Yam para 34 is not explained, and the ruling is non-binding.

---

## B9. Is "הפרטים נלקחו מהאתר הציבורי של העסק" enough as the data source (17ו(א)(3))?

### Takeaway
**GRAY: it is incomplete.** 17ו(א)(3) requires "המקורות שמהם קיבל ... מידע זה". The PPA guideline says the purpose is to let the recipient know how their data reached the database. v1 explains where the **contact details** came from, but not how the **business got onto the list**: a list of business websites compiled with an AI assistant.

### Cited Findings
- 17ו(א)(3): "...והמקורות שמהם קיבל בעל [השליטה ב]מאגר מידע זה". — [TAU text](https://law.tau.ac.il/sites/law.tau.ac.il/files/law_lgbt/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_0.pdf)
- PPA guideline 2/2017:
  - s.12: "הליבה של סימן ב' ... היא זכותו של נמען הדיוור לדעת מנין קיבל המדוור את המידע האישי עליו, ולבקש את מחיקתו".
  - s.19.1.4: one must state "המקור ממנו הגיע המידע", and where the source is the recipient, "רצוי לציין גם את הנסיבות בהן התקבל המידע האישי ממנו ... מפני שייתכן שהנמען איננו זוכר או שלא ידוע לו כיצד הגיע המידע האישי אודותיו למאגר".
  - (PPA guideline 2/2017 updated after amendment 13, local extract; [older gov.il copy](https://www.gov.il/blobFolder/policy/direct_mail_2/he/direct%20mail.pdf))

### Inferences
- A complete source statement would cover both links in the chain and name the actual site. For example: "כתובת אתר העסק שלכם נכללה ברשימת אתרי עסקים בישראל שהכנתי; פרטי הקשר נלקחו מאתר האינטרנט שלכם [דומיין] ביום [תאריך]".
- No rule was found that requires naming the tool used to compile the list (an AI assistant). Whether that must be said is UNKNOWN. Saying it is more transparent and reduces any argument of misleading omission.

### Gaps
- No ruling on how specific the source statement must be. Whether an AI-generated list is a lawful source is question C5 (outside this scope).

---

## B10. Do English words ("Posiblo", "AI") matter legally?

### Takeaway
**UNKNOWN (no rule or ruling found); low risk if the required words are in Hebrew.** 30A(ה) names the Hebrew word "פרסומת", and v1 uses it. The general test is "באופן בולט וברור, שאין בו כדי להטעות". A brand in Latin letters does not obviously fail that test, but writing the name in Hebrew with the Latin form in parentheses is clearest.

### Cited Findings
- s.30A(ה)(1): the words "פרסומת", "בקשת תרומה" or "תעמולה" must appear, "באופן בולט וברור, שאין בו כדי להטעות". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)

### Inferences
- "פוסיבלו (Posiblo)" gives Hebrew clarity and also matches the sender's email domain, which helps identification under (ה)(1)(ב).
- "בינה מלאכותית" instead of "AI" changes nothing legally that I could find, but reads more plainly.

### Gaps
- No ruling found on language or script in 30A labels.

---

## D1. Is a "כן" reply valid prior explicit written consent for future ads? Does the replier need authority?

### Takeaway
- **Written form: OK.** The statute expressly accepts consent "בכתב, לרבות בהודעה אלקטרונית". A "כן" emailed in answer to a request that clearly says what will be sent (ads, about a named topic, by a named channel, from a named advertiser) is express written consent.
- **Authority of the replier: UNKNOWN.** No rule or ruling was found.

### Cited Findings
- s.30A(ב): "בלא קבלת הסכמה מפורשת מראש של הנמען, בכתב, לרבות בהודעה אלקטרונית או בשיחה מוקלטת". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- s.30A(ד)(1): a recipient who consented may "בכל עת ... לחזור בו מהסכמתו". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- Raz (Supreme Court, single justice, obiter "לכאורה"):
  - "המחוקק קבע, כי הנתבע הוא שעליו להראות כי ביקש את הסכמת התובע למשלוח הודעות פרסומת, וכי ההסכמה ניתנה (סעיף 30א(ב) לחוק)".
  - Showing only that the address was entered into the database, without "פרט מזהה נוסף", may not be enough: "נראה לכאורה כי יש צורך ברמה גבוהה יותר של מידע". — [רע"א 1231/17](https://www.law.co.il/media/computer-law/raz3.pdf)

### Inferences
- The scope of the consent is what the request asked. If v2 asks to "send you ads by email about automation and AI services from Posiblo", a "כן" covers that and nothing wider: no SMS, no unrelated products.
- "הנמען" for a business recipient is in practice whoever controls the business's published address. A "כן" from that same address is the strongest proof.
- A "כן" from a different address, or by phone, is weaker. Ask for written confirmation from the address originally contacted. This is an inference.

### Gaps
- No ruling on employee or agent authority to consent for a business.

---

## D2. What proof of consent to keep, in what form, for how long?

### Takeaway
**The rule is clear, the details are not.** The **burden of proving consent is on the advertiser**. The statute sets no record format or retention period. Keep the original reply message with full headers, linked to the exact request version sent, for as long as ads are sent plus the period in which a claim could be brought.

### Cited Findings
- Burden of proof on the advertiser, and the need for identifying detail beyond database entry. — [רע"א 1231/17 רז, para ח](https://www.law.co.il/media/computer-law/raz3.pdf)
- PPA guideline 2/2017 s.19.8 (on deletion requests, by analogy): an electronic request is a written request, and documentation preserves "האפשרות להוכיח את עצם ומועד העלאת הדרישה". — PPA guideline 2/2017 (local extract)

### Inferences
- Keep:
  - the raw .eml of the "כן" (headers, Message-ID, date);
  - the request text and version string;
  - the target URL or form;
  - the send timestamp and the outcome.
  This lets the advertiser show who consented, when, and to what.
- Retention: no 30A period. The civil limitation period under the Prescription Law (7 years for most civil claims) is a likely yardstick. That is an inference: the Prescription Law was not researched here.

### Gaps
- No ruling or regulation on retention of consent records. No regulations under 30A(יא)(1) were found.

---

## D3. Does consent expire? Are there regulations under 30A(יא)?

### Takeaway
**UNKNOWN; none found.** 30A sets no expiry. Consent lasts until withdrawn, which may happen "בכל עת" (30A(ד)(1)). No regulations under 30A(יא) on how consent is given were found.

### Cited Findings
- s.30A(יא): "השר, באישור ועדת הכלכלה של הכנסת, רשאי לקבוע הוראות לעניין ביצוע סעיף זה, לרבות לעניין – (1) אופן מסירת הודעת נמען על הסכמה מפורשת מראש ... (3) אופן מתן הודעת סירוב ... (4) אופן ציון הפרטים ... (5) פרטים נוספים". The subsection only empowers the minister; it does not itself set any rules. — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- A search for regulations under 30A(יא) found none. The result pointed only to general sources ([kolzchut](https://www.kolzchut.org.il/he/%D7%A4%D7%99%D7%A6%D7%95%D7%99_%D7%91%D7%92%D7%99%D7%9F_%D7%9E%D7%A9%D7%9C%D7%95%D7%97_%D7%93%D7%91%D7%A8%D7%99_%D7%A4%D7%A8%D7%A1%D7%95%D7%9E%D7%AA_%D7%9C%D7%9C%D7%90_%D7%94%D7%A1%D7%9B%D7%9E%D7%94_%D7%A9%D7%9C_%D7%94%D7%A0%D7%9E%D7%A2%D7%9F_(%D7%97%D7%95%D7%A7_%D7%94%D7%A1%D7%A4%D7%90%D7%9D)), [chamber.org.il](https://www.chamber.org.il/serviceslobby/legal/74023/115485/)).
- Changes in 2025–2026: the saved current Nevo text of s.30A carries amendment markers up to amendment 76 (2022) and none for amendment 83 (2026). Amendment 83 markers do appear elsewhere in the same Nevo text. — local saved Nevo copy (`law-dl/s30a.txt`, `law-dl/nevo2.txt`), [Nevo](https://www.nevo.co.il/law_html/law01/032_002.htm)

### Inferences
- In practice, treat consent as valid until withdrawn. Unused consent that is many years old is a GRAY area, because a court could doubt it is still "current" consent. No source addresses this.

### Gaps
- I could not confirm from Reshumot that no 30A(יא) regulations exist. The Ministry of Communications FAQ was unreadable (403).

---

## D5. Deadlines for handling a refusal ("הסר")

### Takeaway
- **Under 30A: no grace period, so stop at once.** Any ad sent after a refusal loses all defence (30A(י)(5)(א)).
- **Under Privacy 17ו** (where it applies): delete, and notify the person **in writing** that you did, within **30 days** at the latest.

### Cited Findings
- s.30A(י)(5): "לא תהיה למפרסם הגנה במקרים המפורטים להלן: (א) שיגור דבר הפרסומת נעשה לאחר שניתנה למפרסם הודעת סירוב מאת הנמען". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- 17ו(ד)–(ה): "הודיע אדם ... על דרישתו ... יפעל בעל [השליטה ב]מאגר בהתאם לדרישה ויודיע לאדם, בכתב, כי פעל על פיה"; "(ה) לא הודיע ... תוך 30 ימים מיום קבלת הדרישה, רשאי האדם ... לפנות לבית משפט השלום". — [TAU text](https://law.tau.ac.il/sites/law.tau.ac.il/files/law_lgbt/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_0.pdf)
- PPA guideline s.19.9: "מסגרת הזמן הסבירה ... היא – 30 ימים". s.19.8: "רצוי לשלוח למבקש אסמכתא מתאימה על בקשת המחיקה". — PPA guideline 2/2017 (local extract)
- PPA administrative fine for not complying with a deletion demand under 17ו(ד): ₪15,000 (s.23כו(ב)(5)). — PPA guideline 2/2017 s.21.2 (local extract)

### Inferences
- Under this plan no further ads are ever sent to non-consenters, so 30A exposure after a "הסר" is low. The practical duties are:
  1. Put the business on the suppression list immediately.
  2. Send one short written confirmation with no ad content.
  3. Delete or restrict the record within 30 days.
- How a permanent suppression list fits with deletion is D4, outside this scope.

### Gaps
- No ruling on how fast an advertiser must act on a 30A refusal (for example, a message already in a send queue).

---

## D6. After no reply, may the business ever be approached again (later, another channel, another topic)?

### Takeaway
**NOT OK (by statute text and a non-binding ruling); no exception found.** The exception covers a **"פנייה חד-פעמית מטעם מפרסם"**: one approach by that advertiser, with no time, channel or topic qualifier. A second approach without consent was held unlawful (Hadera, non-binding).

### Cited Findings
- s.30A(ב) wording "פנייה חד-פעמית מטעם מפרסם לנמען שהוא בית עסק, באחת הדרכים האמורות". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)
- Hadera small claims (summary): the first approach was lawful; "בהעדר הסכמה מוכחת של התובע לפניות נוספות, הפנייה השנייה נמצאה שלא כדין"; ₪800. — [law.co.il summary](https://www.law.co.il/computer-law/2011/12/19/igaal-ram-v-geva-barat-ltd/)
- Chazani: the opt-in starting point is "השולח מפר את הוראות החוק החל מהפרסומת הראשונה". The one-time exception is the only gap, and it is narrow. — [Chazani para 16](https://law.haifa.ac.il/wp-content/uploads/2019/01/14019540.M05.pdf)
- 30A(י)(5)(ב): no defence where "המפרסם שיגר בעבר דבר פרסומת לנמען בניגוד להוראות סעיף זה". — [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm)

### Inferences
- "Another channel" or "another topic" from the **same advertiser** is still a second approach. The text counts approaches per advertiser, not per channel or topic. This is an inference, consistent with the plan's own rule of one approach across all channels.
- v1 and v2 promise "לא אפנה שוב". Breaking that promise would also weaken any good-faith argument.
- A human phone call (not automatic dialling) is outside 30A(ב)'s listed means, but that is question F3 and was not researched here.

### Gaps
- No ruling on a second approach after a long interval or through a different channel.

---

## G2/G3. Recommended v2 text and consent flow

### Takeaway
Use a v2 that is (1) a bare question with the advertiser's legal identity, (2) explicit that what is asked is consent to receive **ads**, on a named topic, by a named channel, and (3) complete on every 30A(ה) and 17ו(א) detail, with an explicit refusal address. It should have **no benefits, prices, offers or website link**. Use separate form and email versions, because the refusal and reply routes differ.

### Cited Findings
- The tests the drafts are built on: neutral offer (Chazani para 16, binding); no landing-page or link content (Bat Yam paras 24–32); 30A(ה)(1)(א)–(ג) details; 17ו(א)(1)–(3) details; refusal "בכל עת" with a "כתובת תקפה ... ברשת האינטרנט"; written consent "לרבות בהודעה אלקטרונית" (30A(ב)); burden of proof on the advertiser (Raz). Sources are as cited in B1–B9 and D1–D6 above: [Chazani](https://law.haifa.ac.il/wp-content/uploads/2019/01/14019540.M05.pdf), [Bat Yam](https://www.law.co.il/media/computer-law/keinan8.pdf), [Nevo s.30A](https://www.nevo.co.il/law_html/law01/032_002.htm), [Raz](https://www.law.co.il/media/computer-law/raz3.pdf), [TAU privacy law text](https://law.tau.ac.il/sites/law.tau.ac.il/files/law_lgbt/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_0.pdf).

### Inferences

The drafts below are my own; no court or regulator has approved them. Placeholders in [ ] must be filled before sending, and project hard rule 9 must block sending while any remain.

**v2-form (website contact form).** If the form has a subject field, put this in it: `פרסומת - בקשת הסכמה`

```
פרסומת - בקשת הסכמה חד-פעמית
שלום רב,
שמי [שם מלא], בעל העסק פוסיבלו (Posiblo).
אני מבקש את הסכמתכם לקבל ממני בעתיד, בדואר אלקטרוני, דברי פרסומת על שירותי אוטומציה ובינה מלאכותית לעסקים.
אם אתם מסכימים, שלחו את המילה "כן" בדואר אלקטרוני לכתובת [מייל].
אם אינכם מסכימים, אין צורך להשיב. לא אפנה אליכם שוב.
אתם רשאים בכל עת לסרב לקבלת פניות ממני ולבקש להימחק מהרשימה: שלחו "הסר" לכתובת [מייל], או כתבו אליי לכתובת [כתובת מלאה] או בהודעה לטלפון [טלפון].
זוהי פנייה בדיוור ישיר. כתובת אתר העסק שלכם נכללה ברשימת אתרי עסקים בישראל שהכנתי, ופרטי הקשר נלקחו מאתר האינטרנט שלכם [דומיין].
המפרסם: [שם מלא], פוסיבלו (Posiblo), [כתובת מלאה], טלפון [טלפון], דוא"ל [מייל].
```

**v2-email.** Subject: `פרסומת - בקשת הסכמה`. Body:

```
פרסומת - בקשת הסכמה חד-פעמית
שלום רב,
שמי [שם מלא], בעל העסק פוסיבלו (Posiblo).
אני מבקש את הסכמתכם לקבל ממני בעתיד, בדואר אלקטרוני, דברי פרסומת על שירותי אוטומציה ובינה מלאכותית לעסקים.
אם אתם מסכימים, השיבו להודעה זו במילה "כן".
אם אינכם מסכימים, אין צורך להשיב. לא אפנה אליכם שוב.
אתם רשאים בכל עת לסרב לקבלת פניות ממני ולבקש להימחק מהרשימה: השיבו להודעה זו במילה "הסר", או שלחו "הסר" לכתובת [מייל], או כתבו אליי לכתובת [כתובת מלאה].
זוהי פנייה בדיוור ישיר. כתובת אתר העסק שלכם נכללה ברשימת אתרי עסקים בישראל שהכנתי, וכתובת הדואר האלקטרוני נלקחה מאתר האינטרנט שלכם [דומיין].
המפרסם: [שם מלא], פוסיבלו (Posiblo), [כתובת מלאה], טלפון [טלפון], דוא"ל [מייל].
```

**Why each line is there:**

| Line | Purpose |
|---|---|
| `פרסומת - בקשת הסכמה חד-פעמית` | 30A(ה)(1)(א): "פרסומת" at the start of the message; the email subject also starts with it. "חד-פעמית" signals the 30A(ב) exception and that no follow-up will come. |
| `שמי [שם מלא], בעל העסק פוסיבלו (Posiblo).` | Identifies the advertiser by legal name (B4), with the brand in Hebrew and Latin (B10). |
| `אני מבקש את הסכמתכם לקבל ממני בעתיד, בדואר אלקטרוני, דברי פרסומת על ...` | The core consent question. It says it is **ads** (so a later "כן" is "מפורשת"), names the **channel** (scope of consent) and names the **topic** in the barest terms. No benefits, prices or offer (Chazani "הצעה ניטראלית"). |
| `אם אתם מסכימים, שלחו/השיבו "כן" ...` | A written consent route (30A(ב) "בכתב, לרבות בהודעה אלקטרונית") that produces evidence (Raz). The form version names the address, because a form has no reply channel. |
| `אם אינכם מסכימים, אין צורך להשיב. לא אפנה אליכם שוב.` | Silence is treated as no, which keeps the approach one-time (D6, Hadera). It is a commitment the ledger enforces. |
| `אתם רשאים בכל עת לסרב ... שלחו "הסר" לכתובת [מייל] ...` | 30A(ה)(1)(ג)(1): states the right "בכל עת", a "simple and reasonable" route, and an internet address (the email). It also gives written and alternative routes (30A(ד)(1)). It covers 17ו(א)(2): the right to be deleted plus an address. In the email version, "reply to this message" covers the same-channel reading in Bat Yam para 34. |
| `זוהי פנייה בדיוור ישיר. ... נכללה ברשימת ... ופרטי הקשר נלקחו מ-[דומיין]` | 17ו(א)(1) states it is direct mail; no registry number is needed (PPA s.19.1.1). 17ו(א)(3) gives the sources, covering both the list and the contact details (B9). |
| `המפרסם: [שם מלא], פוסיבלו (Posiblo), [כתובת מלאה], טלפון, דוא"ל` | 30A(ה)(1)(ב) name, address and contact details; 17ו(א)(3) identity and address of the controller. |

**Left out on purpose:**
- A website link: Bat Yam treated a landing page as evidence of an ad.
- Any adjective or benefit ("לחסוך זמן"), any "free" or "trial" offer (Chazani), any personalisation (project rule 9).
- "AI" written in Latin letters in the body.

An optional removal-only URL could be added as a further "כתובת תקפה ברשת האינטרנט". It would have to be part of the fixed template and contain nothing but removal (see B8).

**Recommended consent flow:**

1. **Before sending.**
   - Claim the ledger row for the business across **all** channels. One approach per business, ever.
   - Confirm the recipient looks like a business (A3, another researcher's scope).
   - Confirm no placeholders remain and no suppression-list match exists.
2. **Send** v2-form or v2-email once. Record the version string, the exact text, the target URL or address, the timestamp and the outcome. If the outcome is ambiguous, record `sent_unconfirmed` and never send again (A5, another researcher's scope).
3. **Reply "כן"** (or a clear equivalent, in writing):
   - Save the raw message with full headers.
   - Link it to the request version and to the address it came from.
   - If it came from a different address or person than the one contacted, ask once for confirmation from the original address. This is an inference based on Raz.
   - From then on, send only what was consented to: Posiblo's automation and AI ads, by email. **Every** later ad needs the full 30A(ה) details, starting with "פרסומת" in the subject and at the start, plus the 17ו(א) details.
   - Optionally send one short confirmation ("קיבלנו את הסכמתכם; ניתן לחזור בכם בכל עת: השיבו 'הסר'"), with the full details.
4. **Reply "הסר"** (by any channel, in any wording that clearly refuses):
   - Stop at once: there is no grace period under 30A(י)(5)(א).
   - Add the business to the suppression list.
   - Within 30 days at the latest, delete or restrict the data and send a written confirmation that you acted (17ו(ד)–(ה); PPA s.19.8–19.9). The confirmation must contain no ad content.
5. **No reply:** never approach that business again, in any channel, on any topic, at any time (D6). Close the ledger row as final.
6. **Unclear replies** (questions, "call me", "what do you offer?"):
   - Answering a direct question from the business is GRAY. It is arguably not unsolicited, but no source covers it.
   - The safest course is a single reply that answers only what was asked, carries the full labels, and asks for an explicit "כן" before any ad. This is an inference.

### Gaps
- No court or regulator has reviewed a text like v2.
- Whether "פרסומת" can be required in a site-generated email subject that the sender cannot control (B7) is unresolved.
- Whether an email address alone is a "כתובת תקפה ... ברשת האינטרנט" (B8) is unresolved.
- Questions for the lawyer:
  1. Does a bare naming of the topic ("שירותי אוטומציה ובינה מלאכותית לעסקים") keep the request "ניטראלית" under Chazani? (yes/no)
  2. Does 30A(ה) apply to the one-time request? (yes/no)
  3. For contact-form sends, is "send 'הסר' to [email]" enough without a same-channel route? (yes/no)
  4. Does Bat Yam's civil liability of managers matter if Posiblo is incorporated? (yes/no)
