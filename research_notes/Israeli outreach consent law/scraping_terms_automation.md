# Israeli law on automated website access and automated contact-form submission (C6–C9, A7, robots.txt, G7 input)

Scope: Israel only. Research date 2026-11-27. Not legal advice. Verdicts follow the brief's scale (OK / GRAY / NOT OK / UNKNOWN).

Sources that could not be read:
- gov.il pages returned HTTP 403 to automated fetching, for example https://www.gov.il/he/pages/ai_reg. Following the coordinator's instruction, I made no attempt to get around the refusal. Content from the Privacy Protection Authority (PPA) below therefore comes from law-firm summaries and is marked as secondary.
- The WIPO copy of the Computers Law PDF (https://www.wipo.int/wipolex/edocs/lexdocs/laws/he/il/il089he.pdf) returned an HTTP 301 redirect and no PDF. The statute text below comes from Hebrew Wikisource, which shows amendments up to תשע"ב-2012. Its section 4 wording matches the quote inside the Supreme Court's Ezra ruling.

Correction to the brief: the case the brief calls "ע"פ 8464/14" is actually **רע"פ 8464/14 מדינת ישראל נ' עזרא** (with רע"פ 8617/14), Supreme Court, 15.12.2015. Panel: Deputy President א' רובינשטיין, Justices ח' מלצר and מ' מזוז. I read the full text (law.co.il PDF of the official judgment).

---

## C6: Is breaching a site's terms of use (no commercial use of the contact form, no automated access) a legal problem? (contract, Computers Law s.4, tort)

### Takeaway
**GRAY.** No Israeli ruling was found on submitting a public contact form in breach of terms of use. The Supreme Court in Ezra reads "שלא כדין" broadly, as "use without the owner's consent". On that reading, a clear and real prohibition by the site owner could, in theory, make access unauthorized. The same opinion says that prosecuting someone just for entering a website against small-print terms is not realistic. In contract law, terms the visitor never actively accepted (browsewrap) are, per commentary, usually weak in Israel. I could not verify the Israeli ruling cited for that. The Computers Law tort (s.7) covers only interference and deletion, and s.9 requires proven negligence. A single polite submission is unlikely to fit. Ticking an "I accept the terms" box changes the contract picture (see C8).

### Cited Findings
- **Computers Law s.4 text:** "החודר שלא כדין לחומר מחשב הנמצא במחשב, דינו – מאסר שלוש שנים; לענין זה, "חדירה לחומר מחשב" – חדירה באמצעות התקשרות או התחברות עם מחשב, או על ידי הפעלתו, אך למעט חדירה לחומר מחשב שהיא האזנה לפי חוק האזנת סתר, תשל"ט-1979". Quoted in the ruling at para. 4: [רע"פ 8464/14, law.co.il PDF](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf). Also at [Wikisource](https://he.wikisource.org/wiki/חוק_המחשבים).
- **Definition:** s.1 defines "חומר מחשב" as "תוכנה או מידע". [Wikisource](https://he.wikisource.org/wiki/חוק_המחשבים)
- **Binding holding on "חדירה" (Supreme Court, main opinion by רובינשטיין, para. 17):** the term gets a broad reading, "כך שכל מידע "הנכנס" למחשב – בין שנוצר על-ידי מחשב אחר ובין שנוצר כתוצאה מפעילות המשתמש במחשב – מקים את הדרישה ההתנהגותית בעבירה". [רע"פ 8464/14](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **Binding holding on "שלא כדין" (para. 17):** "באשר לפרשנות המונח "שלא כדין" דומה, כי הפרשנות הראויה למונח היא שימוש במחשב בהיעדר הסכמת בעליו. ודוק, עקיפת מכשול טכנולוגי בהחלט עשויה להיות בעלת משמעות לעניין קיומה של הסכמה לשימוש במחשב". The Court rejected the scholarly view (Kerr) that only circumvention of a technological barrier is criminal: "בית ללא מנעול אינו הפקר – וכך הדין גם במחשב". [same](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **Justice מזוז (para. 4):** the offence occurs when the intrusion is "שלא כדין", "היינו ללא הרשאה של בעל המחשב (או אחר המוסמך ליתן הרשאה), או ללא סמכות חוקית". In para. 6 he declined to take a position on the hypothetical scenarios in רובינשטיין's para. 19. [same](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **Direct reference to website terms of use (para. 18, רובינשטיין; obiter):** "דומני שלא קרוב היום ... בו נראה באולמות בתי המשפט נאשמים שכל חטאם הוא בכך שנכנסו לאתר אינטרנט, אשר בתנאי השימוש שלו נכתב ב"אותיות טל ומטר" (קרי, אותיות קטנות ביותר) שהכניסה אליו אסורה". He leaves trivial cases to prosecutorial discretion and the de minimis defence (s.34יז Penal Law). [same](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **"Substantive consent" test (para. 19, רובינשטיין; obiter):** three scenarios do not meet the offence because "השימוש המתואר בתרחישים נעשה תוך קבלת הסכמה מהותית של בעל המחשב". They are posting a defamatory talkback, a minor falsely claiming to be 18 on a porn site, and browsing a file-sharing site. Example: sites "שמבחינה מהותית מסכימים לכניסת קטינים לאתרם, אך מפרסמים הודעה מן השפה ולחוץ, לפיה כניסתם אסורה". [same](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **Comparative law surveyed:** the opinion reviews US CFAA readings, including a contract-based one under which "שימוש בשירותי דוא"ל המנוגד לתנאי השימוש של חברת הדוא"ל מקים את יסודות העבירה" (citing America Online). The Court did not adopt a specific CFAA test. [same](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **Computers Law tort is narrow:** s.7 makes only these acts a tort: "הפרעה שלא כדין לשימוש במחשב או בחומר מחשב, בכל דרך שהיא" and deleting, altering or disrupting computer material "שלא כדין". Unauthorized access alone is not listed. Under s.9, "לא יינתן פיצוי בתובענה שעילתה בפרק זה, אלא אם כן הוכח כי הנזק נגרם עקב התרשלותו של הנתבע". [Wikisource](https://he.wikisource.org/wiki/חוק_המחשבים)
- **s.2 offence:** "העושה שלא כדין אחת מאלה ... (1) משבש את פעולתו התקינה של מחשב או מפריע לשימוש בו". [Wikisource](https://he.wikisource.org/wiki/חוק_המחשבים)
- **Contract, browsewrap (secondary, unverified):** Israeli commentary says courts generally do not treat browsewrap terms as binding. It cites the Tel Aviv District Court in *מלכה נ' אווה פיננסים*, quoted as saying the court will tend to give greater validity to an online agreement where the user's consent is active (clickwrap). I did not find or read the judgment. [dwo.co.il](https://dwo.co.il/he/%D7%AA%D7%A0%D7%90%D7%99-%D7%A9%D7%99%D7%9E%D7%95%D7%A9-%D7%9C%D7%90%D7%AA%D7%A8/); [y-law.co.il](https://www.y-law.co.il/blog/internet-and-apps/tos-as-contract)
- **Online terms as standard contracts (Supreme Court):** in **רע"א 5860/16 Facebook Inc. נ' בן חמו** (31.5.2018), the Supreme Court examined a forum and choice-of-law clause in Facebook's terms of use. Secondary sources say it did so under the Standard Contracts Law, 1982, and allowed claims against Facebook Ireland to be heard in Israel. I have not read the judgment for its exact holding. It concerns consumer users and a clause the user actively accepted, not browsewrap or scraping. [law.co.il PDF](https://www.law.co.il/media/computer-law/ben_hemo2.pdf); [Mondaq summary](https://webiis05.mondaq.com/contracts-and-commercial-law/723864/facebook-inc-vs-be-chemo-israel-supreme-court-rules-on-the-topic-of-the-choice-of-law-jurisdiction-clauses)
- **Terms cannot create rights the statute denies (secondary):** an Israeli law-firm article (June 2025) says Israeli courts have held "תקנון אתר לא יכול לגבור על כך ואינו יכול ליצור הגנה נוספת 'יש מאין'". This was said in the IP context. It cites ה"פ 11022-03-09 *ג'וב מאסטר נ' אול יו ניד* and 1074/05 *מעריב נ' אול יו ניד*, without court, date or holdings. Not verified. [moticohenadv.com](https://moticohenadv.com/%D7%94%D7%90%D7%9D-%D7%9E%D7%95%D7%AA%D7%A8-%D7%9C%D7%91%D7%A6%D7%A2-%D7%A1%D7%A8%D7%99%D7%A7%D7%AA-%D7%90%D7%AA%D7%A8%D7%99%D7%9D-data-scraping/)

### Inferences
- Under the binding Ezra test (use "בהיעדר הסכמת בעליו", judged by "הסכמה מהותית"), a public contact form is by design an invitation to the public to send messages. Submitting it is very likely inside the owner's substantive consent, even when the message is commercial. The case gets weaker if the site explicitly says the form must not be used for commercial offers, solicitation or bots. Such an explicit statement is the owner's actual non-consent, not a "מן השפה ולחוץ" notice. In that case, criminal exposure under s.4 cannot be ruled out in principle, though the Court itself called prosecution for small-print breaches unrealistic.
- No Israeli case was found applying s.4 to scraping public pages or to contact forms. Applying Ezra to this tool is an inference, not a holding.
- The civil exposure is mainly contract (if terms were accepted, see C8) and the PPA's privacy angle (see C7). It is not the Computers Law tort: s.7 requires interference, and s.9 requires proven negligent damage.
- I found no Israeli "trespass to chattels" tort for computers. I am not able to say whether a general Torts Ordinance cause of action would cover this.

### Gaps
- No Israeli ruling found on: (a) submitting a public contact form against terms of use; (b) browsewrap enforceability in a reported, verifiable judgment (the *Malka* quote is unverified); (c) any Israeli trespass-to-chattels equivalent for servers.
- Nevo and Takdin full-text search was not available, so lower-court scraping rulings may exist that I did not find.

---

## C7: Is automated access to public web pages (scraping), respecting robots.txt, lawful in Israel? (Computers Law, Privacy Protection Law, PPA positions)

### Takeaway
**GRAY.** No statute or binding ruling forbids automated access to public pages, and I found no Israeli court decision on scraping public websites under the Computers Law. Ezra's broad "no owner consent" test is the main criminal-law hook. For pages served publicly with no barrier and no prohibition, that hook is weak. The PPA's April 2025 **draft** AI guideline treats scraping of *personal data* as processing that needs a legal basis. It says scrapers must check that the platform's terms do not forbid scraping, and that site operators must prevent prohibited scraping. The draft is AI-focused, and its relevance to collecting a business's published contact details is an inference. I found no sign that it has been finalized.

### Cited Findings
- **Broad reading of "חדירה" and "שלא כדין":** both are read broadly (Supreme Court, binding), as quoted under C6. [רע"פ 8464/14](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **Law-firm view, June 2025 (secondary):** there is no law or court precedent in Israel broadly banning extraction of information from websites. Scraping does not necessarily breach s.2 ("אין לשבש את פעולתו התקינה של מחשב, או להפריע לשימוש בו"). Courts may enforce a scraping ban where the user is registered "ותנאי השימוש אוסרים זאת במפורש". [moticohenadv.com](https://moticohenadv.com/%D7%94%D7%90%D7%9D-%D7%9E%D7%95%D7%AA%D7%A8-%D7%9C%D7%91%D7%A6%D7%A2-%D7%A1%D7%A8%D7%99%D7%A7%D7%AA-%D7%90%D7%AA%D7%A8%D7%99%D7%9D-data-scraping/)
- **Israeli RSS republishing ruling:** a 2013 Petah Tikva Magistrate's Court ruling (non-binding) held that republishing RSS feed content was not copyright infringement. This is copyright, not the Computers Law. Secondary report only. [Plagiarism Today](https://www.plagiarismtoday.com/2013/02/21/israeli-court-rules-rss-scraping-legal/)
- **PPA draft AI guideline "תחולת הוראות חוק הגנת הפרטיות על מערכות בינה מלאכותית"** (published 28.4.2025). Per the Shibolet law-firm summary (secondary; the gov.il original returned 403):
  - "הסכמה מדעת דרושה אף לצורך עיבוד מידע אישי הנאסף במסגרת כריית מידע אישי מהאינטרנט".
  - Scrapers must check the platform's terms and make sure they "אינם אוסרים על כריית מידע".
  - Using scraped data "בניגוד לתנאי השימוש" without the data subject's consent may breach the ban on processing data from a database without authorization.
  - Digital services "חייבים לנקוט באמצעים למניעת כרייה אסורה של מידע".
  - "כרייה אסורה של מידע אישי ממאגר מידע היא בגדר "אירוע אבטחה חמור"", which must be reported to the PPA.
  - Unauthorized processing may "אף להוות עבירה פלילית" under s.23 as amended by amendment 13.
  [Shibolet](https://www.shibolet.com/טיוטת-הנחיית-הרשות-להגנת-הפרטיות-בעני/)
- **Another secondary summary of the same draft:** it says "כריית מידע כשלעצמה יכולה להוות פגיעה בפרטיות" and "העובדה שמידע פורסם לציבור אינה מהווה כשלעצה הסכמה לעיבוד". It attributes possible breach of s.8ג and a criminal offence under s.23נה. The Shibolet summary does not mention 8ג or 23נה, so these section numbers are unverified. [moticohenadv.com](https://moticohenadv.com/%D7%94%D7%90%D7%9D-%D7%9E%D7%95%D7%AA%D7%A8-%D7%9C%D7%91%D7%A6%D7%A2-%D7%A1%D7%A8%D7%99%D7%A7%D7%AA-%D7%90%D7%AA%D7%A8%D7%99%D7%9D-data-scraping/)
- **Draft status:** IDI sent comments on the draft on 3.8.2025, warning that it presents a regulatory position "שאינו מלווה בהצגת מסד נורמטיבי" and must not extend existing law. A July 2026 Haifa Chamber document still refers to a PPA *draft*. I found no final version. [IDI](https://www.idi.org.il/knesset-committees/60291); [Haifa Chamber PDF](https://haifachamber.org.il/wp-content/uploads/2026/07/המלצות-להתנהלות-הציבור-בשימוש-אישי-בסוכני-בינה-מלאכותית.pdf)
- **International statements:** the Israeli PPA was **not** among the 12 authorities that signed the August 2023 joint statement on data scraping. It **was** one of four new signatories (with Guernsey, Monaco and Spain) of the October 2024 concluding statement. That statement expects platforms to take measures against unlawful scraping. [Hunton](https://www.hunton.com/privacy-and-cybersecurity-law-blog/joint-statement-published-on-data-scraping-and-the-protection-of-privacy); [Swiss FDPIC, concluding statement](https://www.edoeb.admin.ch/en/31102024-concluding-statement-on-data-scraping); [AI-regulation.com](https://ai-regulation.com/?p=5943)

### Inferences
- Fetching public pages at a polite rate, with an honest User-Agent, respecting robots.txt and never passing a login or CAPTCHA, is the lowest-risk pattern under Ezra. The owner serves the page to everyone, and the tool overcomes no barrier. It is not risk-free, because the Court refused to require a barrier for the offence.
- The privacy risk is not in fetching pages. It is in *collecting personal data* (a person's name, a named email such as dana@, a mobile number) from the page. The PPA draft says public availability is not consent and that scraping against the site's terms is a red flag. If the site's terms forbid scraping or collecting contact details, collecting them is GRAY-to-risky under the PPA's (draft) view. Coordinate with C1/C2 (personal data) in other researchers' notes.
- Collecting only what the single message needs (the form URL, or one published address) and not building a dataset of people lowers the privacy exposure. This is an inference, not a cited rule.

### Gaps
- No Israeli court ruling found on scraping public websites under the Computers Law. Nevo and Takdin were not searchable here.
- The final PPA AI guideline, if any, and its exact wording were not readable (gov.il 403).
- Exact section numbers (8ג, 23נה) attributed to the draft are unverified.

---

## C8: May the tool auto-tick a required "I accept the terms / privacy policy" checkbox? What does the sender agree to?

### Takeaway
**GRAY**, with one part close to NOT OK. No Israeli statute or ruling on automated assent was found (UNKNOWN on that point). Ticking a box is the *active* (clickwrap) form of assent that Israeli commentary treats as most likely to bind. So the owner, acting through the tool, should be treated as having accepted that site's terms, including any ban on commercial or automated use. Submitting anyway would then be a knowing breach of an accepted contract. It would also show actual non-consent of the owner in Ezra terms. Ticking a box whose terms you have not read is not "bypassing access control". But it removes the "I never agreed" defence available against browsewrap.

### Cited Findings
- **Active consent is preferred:** Israeli commentary says courts give more weight to active (clickwrap) consent than to browsewrap. It cites *Malka v. Ava Financial* (Tel Aviv District Court, quote unverified). [dwo.co.il](https://dwo.co.il/he/%D7%AA%D7%A0%D7%90%D7%99-%D7%A9%D7%99%D7%9E%D7%95%D7%A9-%D7%9C%D7%90%D7%AA%D7%A8/); [y-law.co.il](https://www.y-law.co.il/blog/internet-and-apps/tos-as-contract)
- **Ezra links terms to consent:** the Supreme Court ties "שלא כדין" to the owner's consent ("הסכמה מהותית"), as quoted under C6. [רע"פ 8464/14](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **Standard-contracts review:** online terms are reviewed as standard contracts. Per secondary sources, a clause can be struck under the Standard Contracts Law (Facebook v. Ben Hamo, Supreme Court, 31.5.2018; consumer context). [law.co.il PDF](https://www.law.co.il/media/computer-law/ben_hemo2.pdf)
- **PPA draft and terms:** the draft treats breach of a platform's terms during data collection as relevant to lawfulness (secondary). [Shibolet](https://www.shibolet.com/טיוטת-הנחיית-הרשות-להגנת-הפרטיות-בעני/)

### Inferences
- A tick on a "privacy policy" box mostly concerns how *the site* will process *the sender's* data (name, email, phone). The sender's risk there is low.
- A tick on a "terms of use" box may bind the sender to restrictions such as "לא לשלוח פרסומות", "שימוש לא מסחרי" or "אסור שימוש באמצעים אוטומטיים". It may also bind the sender to a forum clause or an indemnity. A Standard Contracts Law review could cut back unfair clauses, but that is a defence, not a permission.
- Software acting for the owner does not change who is bound. I found no Israeli source suggesting that automated assent is void. Treat it as the owner's own assent.
- Practical consequence: before ticking, the tool (or the owner manually) must read the linked terms and skip the site if they restrict commercial messages, solicitation or automated use. Simplest safe rule: do not auto-submit forms whose required checkbox links to terms of use. Send them to manual review, or skip them.

### Gaps
- No Israeli ruling on assent given by a bot or software agent.
- No reported Israeli ruling found enforcing a website's "no commercial use of contact form" clause.

---

## C9: Is a "no solicitation" / "אין לשלוח פרסומות" notice on a website a refusal notice (הודעת סירוב) under s.30A(ד)?

### Takeaway
**UNKNOWN** (no ruling found). On the statute's wording it is **probably not** a formal הודעת סירוב. That is a notice the recipient gives *to the advertiser* after consent or an opt-out offer. Even so, it is legally relevant: it is very likely the owner's expressed non-consent for using the site or form for solicitation (Ezra), possibly a contract term, and strong evidence against good faith. Continuing to skip such sites is the right practice.

### Cited Findings
- **s.30A(ד)(1) text** (current text, read from the Nevo extract): "הסכים הנמען לקבל דברי פרסומת לפי הוראות סעיף קטן (ב) או לא הודיע על סירובו לקבלם לפי הוראות סעיף קטן (ג), רשאי הוא, בכל עת, להודיע למפרסם על סירובו לקבל דברי פרסומת, דרך כלל או מסוג מסוים, ולחזור בו מהסכמתו, ככל שניתנה (בסעיף זה – הודעת סירוב); ... הודעת הסירוב תינתן בכתב או בדרך שבה שוגר דבר הפרסומת, לפי בחירת הנמען". Source: s30a.txt extract supplied with the brief (Nevo text), local file C:\Users\meirn\AppData\Local\Temp\claude\f34d24dbda83d666\35fab18c-04ab-4bd2-b6af-6ffae10e519f\scratchpad\law-dl\s30a.txt.
- **No defence after a refusal:** under s.30A(י)(5)(א), "לא תהיה למפרסם הגנה" where "שיגור דבר הפרסומת נעשה לאחר שניתנה למפרסם הודעת סירוב מאת הנמען כאמור בסעיף קטן (ד)". [same extract]
- **The one-time business exception applies only to a "הצעה להסכים לקבל דברי פרסומת"** (s.30A(ב), last sentence). [same extract]
- **s.30A(יג):** "אין בהוראות סעיף זה כדי לגרוע מהוראות כל דין". So other law (Computers Law, contract, privacy) still applies. [same extract]
- **Ezra:** use against the owner's real wish is "שלא כדין". A notice that is only "מן השפה ולחוץ" does not negate substantive consent. A sincere "do not send ads" notice is the opposite case. [רע"פ 8464/14](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- A targeted search for Israeli rulings on a general website notice as a refusal found nothing. [search, no primary result]

### Inferences
- The (ד) definition has three parts: the recipient "להודיע למפרסם", it is triggered after consent or a (ג) opt-out offer, and it may be given "דרך כלל". Together these suggest a refusal directed at advertisers generally could arguably be "דרך כלל". But a notice posted on one's own site was not given *to* a particular advertiser, so it most likely does not trigger the (י)(5)(א) no-defence rule. A court could still weigh it against the sender: knowledge, no good faith, and the amount of exemplary damages under (י)(3).
- Also consider whether a notice like "אין לשלוח פרסומות" is a prior refusal that defeats the "offer to consent" exception. The exception is itself an offer to consent, and a recipient who has said in advance "no ads" has arguably already answered it. No source either way.
- Recommendation for the tool: keep skipping, and broaden detection to similar phrases ("ללא פניות שיווקיות", "אין לפנות בהצעות מסחריות", "no solicitation", "no sales pitches"), in the form's labels as well as the page text.

### Gaps
- No ruling or Ministry of Communications position found on whether a published general notice is a הודעת סירוב. The Ministry's FAQ (gov.il) was not readable (403).

---

## A7: Does sending automatically by software change the legal analysis (spam law, Computers Law)?

### Takeaway
**Spam law: OK, no change.** s.30A turns on the *channel* (fax, automatic dialing, electronic message, SMS) and on consent, not on whether a human or a script composes or submits the message. **Computers Law: GRAY, mild increase.** Ezra's reading of "חדירה" covers any information entering a computer, manual or automated alike. Automation raises the risk only through volume and load (s.2 "שיבוש"/"הפרעה", s.7 tort) and through the scale-based "מכפיל נזק" reasoning. The tool's per-host delays, single submission and caps address this.

### Cited Findings
- **s.30A(ב) channels:** "לא ישגר מפרסם דבר פרסומת באמצעות פקסימיליה, מערכת חיוג אוטומטי, הודעה אלקטרונית או הודעת מסר קצר, בלא קבלת הסכמה מפורשת מראש של הנמען". "מערכת חיוג אוטומטי" is defined for voice calls ("לשם העברת מסר קולי מוקלט"). So a form submission or email by script is not "automatic dialing"; at most it is an "הודעה אלקטרונית". [s30a.txt extract]
- **s.30A(י)(5)(ג):** no defence where the message was sent "לפי רשימה של מענים או מספרי טלפון ... שהורכבו בהתאם לרצף אקראי של אותיות, ספרות או סימנים אחרים". This is about randomly generated address lists, which Posiblo does not use. [same extract]
- **Ezra, para. 17:** "כל מידע "הנכנס" למחשב – בין שנוצר על-ידי מחשב אחר ובין שנוצר כתוצאה מפעילות המשתמש במחשב – מקים את הדרישה ההתנהגותית בעבירה". That is, machine-generated and human-generated input are treated alike. [רע"פ 8464/14](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **Ezra, para. 19:** the computer offence is justified where technology acts as a "מכפיל נזק". Example: "אדם המתקשר לטלפון נייד שוב ושוב ... לא יואשם בעבירה; אך אדם השולח תמונות ללא הרף למכשיר טלפון נייד עשוי להיכנס בגדרה". [same](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **Computers Law s.2(1):** "משבש את פעולתו התקינה של מחשב או מפריע לשימוש בו". Tort s.7(1): "הפרעה שלא כדין לשימוש במחשב". [Wikisource](https://he.wikisource.org/wiki/חוק_המחשבים)

### Inferences
- Automation does not create a new violation under s.30A. It *raises scale*, and with it the damages exposure under (י)(3)(ג) "היקף ההפרה", and the class-action attractiveness. That is a reach and volume issue, not a legal-category change.
- Under the Computers Law, one submission per site with delays and no repeat is far from "שיבוש" or "מכפיל נזק". Rapid repeated submissions would not be.

### Gaps
- No Israeli ruling found that discusses automated (bot) submission of contact forms specifically.

---

## robots.txt: does Israeli law or a regulator give it legal weight?

### Takeaway
**UNKNOWN.** No Israeli statute, ruling or regulator text mentioning robots.txt was found. Under Ezra's consent test, a robots.txt Disallow is plausibly evidence of the owner's (non-)consent to automated access, so respecting it is protective. Ignoring it could support a "no consent" finding. Foreign case law (US, Ziff Davis v. OpenAI, S.D.N.Y., Dec. 2025) held robots.txt is not a "technological measure" under the DMCA. That is context only and not Israeli law.

### Cited Findings
- **Search:** a search for Israeli rulings on robots.txt returned none. The only decision surfaced was the US *Ziff Davis v. OpenAI* (S.D.N.Y., Dec. 2025), which held robots.txt is not a DMCA access-control measure. [Eric Goldman blog](https://blog.ericgoldman.org/archives/2025/12/are-robots-txt-instructions-legally-binding-ziff-davis-v-openai.htm); [Pearl Cohen](https://www.pearlcohen.com/u-s-courts-step-in-to-rule-on-digital-copyright-ai-and-online-child-protection-issues/)
- **Ezra:** "עקיפת מכשול טכנולוגי בהחלט עשויה להיות בעלת משמעות לעניין קיומה של הסכמה". The Court does not mention robots.txt. [רע"פ 8464/14](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **Concluding international statement (Oct 2024, PPA a signatory):** expects platforms to use measures against automated scraping. robots.txt is not specifically confirmed in what I read. [Swiss FDPIC](https://www.edoeb.admin.ch/en/31102024-concluding-statement-on-data-scraping)

### Inferences
- Keep robots.txt compliance. It costs little and is the best available evidence that the tool followed the owner's machine-readable wishes.
- Note the limit: robots.txt governs crawling, not form submission. A site that allows crawling but says "no solicitation" in its terms or page text still signals non-consent to solicitation.

### Gaps
- No Israeli authority at all on robots.txt.

---

## G7 input: practices to avoid, and safer alternatives (derived from the above)

### Takeaway
The legally riskiest practices are the ones that turn "the owner's public invitation" into "use against the owner's expressed wish". That means ticking terms boxes without reading them, ignoring "no solicitation" or "no bots" statements, and repeated or high-rate automated access.

### Cited Findings
- **Binding consent test:** the test is "use without the owner's consent", judged by substantive consent (Ezra, Supreme Court, binding on lower courts). [רע"פ 8464/14](https://www.law.co.il/media/computer-law/ezra_elyon_Zer3tbi.pdf)
- **PPA draft:** check the platform's terms before collecting personal data. Scraping in breach of terms is treated as unauthorized (secondary). [Shibolet](https://www.shibolet.com/טיוטת-הנחיית-הרשות-להגנת-הפרטיות-בעני/)
- **Active acceptance binds more:** clickwrap is more binding than browsewrap (commentary; ruling unverified). [dwo.co.il](https://dwo.co.il/he/%D7%AA%D7%A0%D7%90%D7%99-%D7%A9%D7%99%D7%9E%D7%95%D7%A9-%D7%9C%D7%90%D7%AA%D7%A8/)

### Inferences (practices to avoid → safer alternative)
1. **Auto-ticking a required "I accept the terms of use" box without reading the terms** → skip such forms, or send them to manual review. A human reads the linked terms. Submit only if the terms contain no ban on commercial, solicitation or automated use. Log the terms URL, a hash of the terms and the date. A "privacy policy" acknowledgement box is lower risk, but should still be logged.
2. **Submitting a form where the site's terms or page text forbid commercial messages, solicitation or automated access** → treat as a skip status (the existing `no_solicitation` status, extended to terms-of-use bans). Check the terms page as well as the contact page. The tool currently scans only for solicitation phrases.
3. **Ignoring robots.txt, or treating a fetch error as permission** → keep current behaviour: fail closed.
4. **Any workaround of CAPTCHA, honeypot fields, rate limits, IP blocks, login or JS challenges** → never do it. Under Ezra, getting past a barrier is the aggravated case and strong evidence of no consent. Record the status and move on (already a hard rule).
5. **High-rate or repeated submissions** (risk under s.2 / s.7, "מכפיל נזק") → keep one submission per site, per-host delay, the circuit breaker, and no automatic retry.
6. **Collecting more personal data than the one message needs** (named staff emails, mobile numbers into a dataset) → collect only the form endpoint or a generic business address at send time. Do not keep personal contact data beyond the ledger's need. Coordinate with the C1–C4 notes.
7. **Disguised User-Agent or anonymised origin** → keep the honest User-Agent with a contact URL. It supports good faith and lets owners object.
8. **Treating a "no solicitation" notice as legally irrelevant just because it may not be a formal הודעת סירוב** → treat it as a refusal for all channels (form, email, SMS) and add the domain to the permanent do-not-contact list.

### Gaps
- Whether a lawyer would accept "manual review then submit" for terms-checkbox forms as low risk is a question for the lawyer (G9). Suggested yes/no question: "If a site's terms of use, which we tick to accept, do not forbid commercial or automated use, is a single automated consent-request submission through its form free of Computers Law s.4 and contract exposure?"
