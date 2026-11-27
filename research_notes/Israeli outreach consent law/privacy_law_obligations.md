# Privacy Protection Law 1981 (after amendment 13) obligations for Posiblo's one-time consent-request outreach

Scope: Israel only. Status checked as of 27 November 2026. "The law" = חוק הגנת הפרטיות, התשמ"א-1981 as amended by חוק הגנת הפרטיות (תיקון מס' 13), התשפ"ד-2024 (ס"ח 3287, 14.8.2024, in force 14.8.2025).

Source notes (read first):
- Amendment 13 official text (Reshumot, ספר החוקים 3287) was downloaded and read: [ס"ח 3287 on gov.il](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf). Knesset copy: [fs.knesset.gov.il 25_lsr_4810658](https://fs.knesset.gov.il/25/law/25_lsr_4810658.pdf) (not fetched; linked from Wikisource).
- Consolidated law text used for sections that amendment 13 did not rewrite: [Wikisource, חוק הגנת הפרטיות](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA). Wikisource is an unofficial consolidation; I cross-checked its definitions and sections 8 and 8א against ס"ח 3287 and they match. Nevo was not used.
- Data Security Regulations: [Wikisource, תקנות הגנת הפרטיות (אבטחת מידע), התשע"ז-2017](https://he.wikisource.org/wiki/%D7%AA%D7%A7%D7%A0%D7%95%D7%AA_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_(%D7%90%D7%91%D7%98%D7%97%D7%AA_%D7%9E%D7%99%D7%93%D7%A2)) (official source cited there: ק"ת תשע"ז 1022, [olaw copy](https://olaw.org.il/takanot/takanot-7809.pdf), not fetched). I did not check whether the regulations' wording was changed after amendment 13. The Wikisource text still uses pre-amendment terms such as "בעל מאגר" and "הרשם".
- Privacy Protection Authority (הרשות להגנת הפרטיות, "the Authority") guideline 2/2017 on direct mail, "נוסח מעודכן בעקבות תיקון 13": read from the local text extract supplied by the coordinator (scratchpad `pdf-out/webfetch-1795770341650-zpfv46.u8.txt`). I do not have its gov.il URL. Below it is cited as "[Guideline 2/2017 (updated)]".
- Two gov.il HTML pages refused automated access (HTTP 403) and could not be read: https://www.gov.il/he/pages/database_mails_and_names and https://www.gov.il/he/pages/ai_reg. A plain curl of the first returned only a JavaScript shell. I did not try to get around this. I used the BlobFolder PDFs and search-result snippets instead.

---

## C1. Is collecting a business's email or contact form from its own public website, and using it for one message, lawful under the Privacy Protection Law? (s. 1, 2(9), 8, 11, the "duty to notify" opinion)

### Takeaway
Verdict: **GRAY, low to moderate risk; OK for corporations.** For a business that is a corporation, the law's personal-data provisions do not apply to data about the corporation itself, because "אדם" excludes a corporation. They do apply to a named employee's address. For sole proprietors and named addresses, no statute or Authority text expressly allows or forbids collecting contact details that a business publishes on its own site and using them for one approach. The Authority's general position is that processing needs consent or legal authority, and that implied consent covers only uses reasonably linked to the purpose of publication. It has expressly left "open sources" collection undecided.

### Cited Findings
- Section 1: "לא יפגע אדם בפרטיות של זולתו ללא הסכמתו." — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Section 2(9), one of the listed privacy infringements: "שימוש בידיעה על עניניו הפרטיים של אדם או מסירתה לאחר, שלא למטרה שלשמה נמסרה". — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Section 3, after amendment 13, defines "אדם" "לענין סעיפים 2, 13, 14, 15א, 17ב, 17ב1, 17ב2, 17ו, 23ב, 23מו, ו־25, וכן לעניין ההגדרות 'דיוור ישיר', 'מאגר מידע', 'מזהה ביומטרי', 'מידע אישי' ו'מידע בעל רגישות מיוחדת' – למעט תאגיד". — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Section 3: "'הסכמה' – הסכמה מדעת, במפורש או מכללא". — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- New section 8(b): "לא יעבד אדם מידע אישי במאגר מידע אלא למטרת המאגר שנקבעה לו כדין." Section 8(d)(1): a controller "לא יעבד מידע אישי במאגר מידע ... אם המידע האישי הכלול במאגר המידע נוצר, התקבל, נצבר או נאסף בניגוד להוראות חוק זה או להוראות כל דין אחר המסדיר עיבוד מידע." Section 8(d)(3): this does not apply "על הפרת דין קלת ערך בנסיבות העניין". Section 8(c): "לא יעבד אדם מידע אישי ממאגר מידע ללא הרשאה מאת בעל השליטה במאגר המידע או בחריגה מהרשאה כאמור." — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- "Processing" is defined broadly: "'עיבוד', 'שימוש' – כל פעולה שמבוצעת על מידע אישי, לרבות קבלתו, איסופו, אחסונו, העתקתו, עיון בו, גילויו, חשיפתו, העברתו, מסירתו או מתן גישה אליו". — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- Consent opinion of 25.2.2026, §3: "חוק הגנת הפרטיות קובע כי איסוף ושימוש במידע אישי ... הכרוכים בפגיעה בפרטיות יכולים להיעשות מכוח הסמכה בדין או בהסכמת נושא המידע." §9: section 8(d)(1) "תחול על מידע אישי שנאסף אגב פגיעה בפרטיות שלא מתוקף הסכמה תקפה לפי החוק, אלא אם קיימת הסמכה בדין לאיסופו." — [גילוי דעת בנושא הסכמה, 25.2.2026](https://www.gov.il/BlobFolder/legalinfo/consent-2026/he/cpncent-2025.pdf)
- Same opinion on implied consent, §42: online implied consent "תיחשב תקפה רק בנסיבות בהן קיים קשר סביר בין מטרות איסוף המידע ואופן השימוש בו למאפייני אותו השירות". §44: "שתיקתו של אדם, או העדר מחאה מצדו ... כשלעצמם, לא יכולים ללמד על הסכמה תקפה". §46: "הסכמה מכללא לשימוש במידע למטרה אחת, אין בה בכדי להתיר שימוש במידע למטרה אחרת". — [consent opinion 2026](https://www.gov.il/BlobFolder/legalinfo/consent-2026/he/cpncent-2025.pdf)
- Same opinion, §43: the Supreme Court in Gutsman held that agreeing to disclose details to certain parties is not implied consent to disclose them to others (ע"א 1697/11 גוטסמן נ' ורדי, 23.1.2013, as cited there). — [consent opinion 2026](https://www.gov.il/BlobFolder/legalinfo/consent-2026/he/cpncent-2025.pdf)
- Section 11 applies only to an approach to a person for data: "פניה לאדם לקבלת מידע אישי לשם עיבודו במאגר מידע תלווה בהודעה שיצויינו בה – (1) אם חלה על אותו אדם חובה חוקית למסור את המידע, או שמסירת המידע תלויה ברצונו ובהסכמתו ומהי תוצאת אי־ההסכמה; (2) המטרה אשר לשמה מבוקש המידע; (2א) שמו של בעל השליטה במאגר המידע, ודרכי ההתקשרות עימו; (3) למי יימסר המידע ומטרות המסירה; (4) קיומן של זכות עיון ... לפי סעיף 13 ושל זכות לבקש תיקון ... לפי סעיף 14." — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Duty-to-notify opinion (18.7.2022, updated after amendment 13), §4: section 11 "חלות בכל מקום בו איסוף מידע אישי על אודות אדם נעשה על יסוד פנייה אליו לקבלת המידע". Footnote 2: "יצוין כי ישנה לכאורה גם אפשרות של איסוף מידע ממקורות גלויים וזאת ללא צורך בפנייה לנושא המידע ולקבלת הסכמתו המפורשת. סוגיה זו חורגת מתחולת מסמך זה." Footnote 3: the duty applies to approaches made "בעל-פה, באופן טלפוני או באמצעות הרשת". — [חובת יידוע, notify13.pdf](https://www.gov.il/BlobFolder/legalinfo/duty_to_notify/he/notify13.pdf)
- Penalties for a missing section 11 notice. Section 23כו(ג)(1)(א) allows an administrative fine of 50 ₪ times the number of people approached. Section 23כו(ג)(2): "היה סכום העיצום הכספי לפי פסקה (1) קטן מ־30,000 שקלים חדשים, רשאי ראש הרשות להטיל ... עיצום כספי בסכום של 30,000 שקלים חדשים." Section 15א(א)(2) allows court damages without proof of harm, up to 10,000 ₪, only where the person asked the controller for the notice and 30 days passed. — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- In the AI-systems draft (28.4.2025), the Authority treats scraping as needing informed consent. §6.3.5: "גם כריית מידע אישי מרשת האינטרנט (scraping) לצורך עיבודו במערכת בינה מלאכותית ... כרוכה בפגיעה אסורה בפרטיות, אם לא ניתנה לכך הסכמה מדעת של נושא המידע". It goes on: "גם כאשר אדם מפרסם באופן יזום מידע אודותיו באינטרנט ... ניתן לייחס לו הסכמה מדעת לכריית המידע ולשימוש בו למטרות כלליות נוספות, רק אם תנאי השימוש של האתר לא מייחדים במפורש או במשתמע את השימוש במידע למטרה ספציפית אחרת". — [טיוטת הנחיה, בינה מלאכותית, 28.4.2025](https://www.gov.il/BlobFolder/rfp/ai_reg/he/ai%20regu_draft.pdf)
- Same draft, footnote 26: scraping a site contrary to its terms of use and without the data subject's consent "גם מפרה לכאורה את האיסור על עיבוד מידע ממאגר ללא הרשאת בעל השליטה במאגר, שנוסף בסעיף 8(ג) ... ועלולה להגיע גם כדי עבירה פלילית לפי סעיף 23נה". — [AI draft 2025](https://www.gov.il/BlobFolder/rfp/ai_reg/he/ai%20regu_draft.pdf)
- Direct-mail guideline §6. Where data comes from the data subject, using it for direct mail needs prior consent; otherwise the controller breaches s. 2(9), 8(ד)(1) and 11. "במלים אחרות, אין לאסוף מידע אישי על אדם אלא אם כן הוא מסכים לאיסוף המידע ולשימושים השונים". — [Guideline 2/2017 (updated)]
- Contact details count as protected private matters when used without consent. The Authority's opinion on "מידע" says: "בפסיקה נקבע כי גם נתונים כגון כתובת מגורים ומספר טלפון מהווים 'ידיעה על ענייניו הפרטיים של אדם' וראויים להגנה על פי החוק, אם לא ניתנה הסכמה של נושא המידע לעשות בהם שימוש" (citing עע"מ 2820/13 רוזנברג; עת"מ 67403-01-19 הר שמש). — [note_privacy_tikon13.pdf](https://www.gov.il/BlobFolder/legalinfo/legat_terms2022/he/note_privacy_tikon13.pdf)

### Inferences
- If the business is a company (בע"מ) or another corporation, data about the business itself falls outside "מידע אישי", "מאגר מידע", "דיוור ישיר" and s. 2, because "אדם" excludes a corporation. Privacy-law risk then arises only where the address or phone identifies an individual, such as dana@company or the owner's mobile.
- For sole proprietors and named people, the strongest argument for lawfulness is implied consent tied to purpose. A business that publishes an email or contact form on its own site invites contact about business matters, and one business inquiry is reasonably linked to that purpose (consent opinion §42, §46). The weak point is that the Authority's AI draft and consent opinion read implied consent narrowly. A court could also find that a marketing-related approach goes beyond the purpose of publication (s. 2(9)). No ruling on exactly this situation was found, so the verdict is GRAY, not OK.
- The current design keeps the risk low: one message, contact details taken only from the business's own site, no enrichment, no profiling, skipping "no solicitation" sites, and honoring robots.txt. Respecting a site's terms of use matters because of the Authority's s. 8(ג) reading in the AI draft, footnote 26.
- Section 11 is triggered only by "פניה לאדם לקבלת מידע אישי". Reading public pages is not such an approach. However, the consent request asks the recipient to reply, and Posiblo then stores the reply (replier name, email, the "כן"). That arguably is an approach to obtain personal data for a database. The safe course is to add a short s. 11 notice to the message, or a link to a privacy notice: reply is voluntary, purpose, controller name and contact, no transfer to others, rights under s. 13–14.

### Gaps
- No court ruling (Supreme, district or magistrate) was found on collecting business contact details from a business's own website for a marketing or consent approach under s. 2(9) or s. 8. One search returned only unrelated small-claims material, which I did not read.
- The Authority has not published a position on "open sources" collection. The duty-to-notify opinion, footnote 2, expressly leaves it out of scope.
- The AI guidance is a draft dated 28.4.2025. I did not find whether a final version was issued by November 2026, because the gov.il page ai_reg returned 403.

---

## C2. Is a business email address "מידע אישי"? Generic (info@) vs a person's (dana@, a sole proprietor's Gmail)

### Takeaway
A person's address (dana@, a sole proprietor's Gmail or own-domain address, or the owner's mobile) **is personal data**, because it relates to an identified or identifiable individual. A generic address of a **corporation** (info@company) is **generally not personal data of the corporation**, since "אדם" excludes a corporation for this definition. It becomes personal data if it identifies or points to an individual, for example a one-person company or a mailbox clearly used by one named person. The Authority treats email addresses as personal data. Practical rule: treat every collected address as personal data.

### Cited Findings
- Amendment 13 definition: "'מידע אישי' – נתון הנוגע לאדם מזוהה או לאדם הניתן לזיהוי; לעניין הגדרה זו, 'אדם הניתן לזיהוי' – מי שניתן לזהותו במאמץ סביר, במישרין או בעקיפין, ובכלל זה באמצעות פרט מזהה, כגון שם, מספר זהות, מזהה ביומטרי, נתוני מיקום, מזהה מקוון, או נתון אחד או יותר הנוגע למצבו הפיזי, הבריאותי, הכלכלי, החברתי או התרבותי". — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- For the definition of "מידע אישי", "אדם" means "למעט תאגיד". — [Wikisource consolidated law, s. 3](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- The Ministry of Justice / Authority guide to amendment 13 says the new definition is broad: "כל נתון הנוגע לאדם מזוהה או לאדם הניתן לזיהוי". — [מדריך תיקון 13](https://www.gov.il/BlobFolder/reports/guide_tikon13_professional/he/tikun%2013%20_170825.pdf)
- The Authority's opinion on "מידע" and "ידיעה על ענייניו הפרטיים" (20.12.2022, with a 2025 note on amendment 13) states that amendment 13 replaced the old definition, so parts of the opinion on the old definition "אינם רלוונטיים עוד". It also says: "ככלל, גם כתובת הדוא"ל של אדם עשויה לעלות כדי מידע, כאשר ניתן להסיק ממנה פרטים נוספים על אדם" (footnote 45 refers to the opinion "האם אוסף של שמות וכתובות דוא"ל מהווה 'מאגר מידע'?"). — [note_privacy_tikon13.pdf](https://www.gov.il/BlobFolder/legalinfo/legat_terms2022/he/note_privacy_tikon13.pdf)
- The Authority page "גם כתובות דואר אלקטרוני הן מידע אישי לפי חוק הגנת הפרטיות" could not be read (403). According to search-result snippets of that page (dated 28.11.2018, updated 29.04.2025), the opinion holds that "אוסף של שמות וכתובות דואר אלקטרוני אינו נכנס לגדר אותו חריג ולכן מהווה מאגר מידע", because "ניתן ללמוד מכתובות דואר אלקטרוני מידע אישי כמו תחום עיסוק, מצב משפחתי, גיל ועוד". Caution: these come from a search index, and the search tool said it may have paraphrased. They are not verified against the page. — [gov.il database_mails_and_names (not readable, 403)](https://www.gov.il/he/pages/database_mails_and_names)
- Secondary reports of the same opinion. Protocol: "כתובת אימייל מהווה מפתח המאפשר לזהות אדם בוודאות מסויימת" and "שילוב של שם פרטי עם כתובת דואר אלקטרוני מהווה שילוב של מידע אישי". Globes notes the opinion was published without prior public consultation. — [protocol.co.il](https://protocol.co.il/email-address-personal-info/); [Globes](https://www.globes.co.il/news/article.aspx?did=1001263625)
- Courts treat a mobile number as part of a person's private matters: "לעניין מספר הטלפון הנייד של אדם כנכלל בליבת ענייניו הפרטיים ראו עת"מ 67403-01-19 הר שמש" (as cited by the Authority). — [note_privacy_tikon13.pdf](https://www.gov.il/BlobFolder/legalinfo/legat_terms2022/he/note_privacy_tikon13.pdf)

### Inferences
- A sole proprietor (עוסק פטור or מורשה) is a natural person, not a corporation, so every contact detail of that business is personal data of the owner. This covers most freelancers and one-person clinics.
- info@ at a company with employees is probably not personal data. info@ at a company whose only staff member is the owner is arguably "ניתן לזיהוי במאמץ סביר".
- The tool cannot reliably tell whether a business is a corporation or a natural person. The ledger and suppression list should therefore be handled as personal data throughout.

### Gaps
- The full text of the email-address opinion could not be read (403). I have not verified whether its 29.04.2025 update changed the reasoning for amendment 13, or whether it distinguishes generic from personal or business addresses.
- No Authority text or ruling was found that addresses generic role addresses (info@, office@) of corporations specifically.

---

## C3. Is the ledger a "מאגר מידע" after amendment 13? Registration or notice to the Authority? Direct-mail rules (17ד, 17ה, 17ו)

### Takeaway
The ledger is **probably a "מאגר מידע"** to the extent it holds personal data (sole proprietors, named addresses, replies). The contact-details exemption probably does not apply, because the ledger also holds status (sent, opted_out, consent) and the Authority reads emails as revealing additional information. Verdict on that point: GRAY, so treat it as a database. **Registration: not required. Notice to the Authority: not required. DPO: not required.** Posiblo's database is not mainly for passing data to others, Posiblo is not a public body, it is far below 10,000 people, and it holds no special-sensitivity data. **17ד and 17ה apply only to a database used for direct-mail *services* (for others), so they do not legally apply. 17ו(א)–(ה) applies to every direct-mail approach to an individual.**

### Cited Findings
- New definition: "'מאגר מידע' – אוסף פרטי מידע אישי המעובד באמצעי דיגיטלי, למעט אחד מאלה: (1) אוסף לשימוש אישי שאינו למטרות עסק; (2) אוסף הכולל רק שם, מען ודרכי התקשרות, לגבי 100,000 בני אדם או פחות, שאינו מלמד כשלעצמו על מידע אישי נוסף לגבי בני האדם ששמותיהם כלולים בו, ובלבד שלבעל האוסף או לתאגיד בשליטתו אין אוסף אחר הכולל פרטי מידע אחרים לגבי אותם בני אדם". — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- Section 8א(א)(1), registration: "מאגר מידע חייב ברישום בהתקיים אחד מאלה: (א) מטרתו העיקרית היא איסוף מידע אישי לשם מסירתו לאחר כדרך עיסוק או בתמורה, לרבות שירותי דיוור ישיר, ויש במאגר מידע אישי על יותר מ־10,000 בני אדם; (ב) בעל השליטה במאגר המידע הוא גוף ציבורי ...". — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- Section 8א(ב)(1), notice: "עלה מספר בני האדם שיש על אודותיהם מידע בעל רגישות מיוחדת במאגר מידע שאינו מאגר חייב ברישום ... על 100,000, יודיע בעל השליטה במאגר המידע לרשות, בתוך 30 ימים ...". Section 8א(ג): the section does not apply "על מאגר שאין בו אלא מידע שפורסם לרבים על פי סמכות כדין או שהועמד לעיון הרבים על פי סמכות כדין". — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- The amendment 13 guide: "חובת רישום מאגרי מידע ביחס לגופים במגזר הפרטי בוטלה כמעט לחלוטין". Also: "העובדה שמאגר מידע לא יהיה חייב ברישום ... אינה פוטרת את המאגר או את בעל השליטה בו מקיום כל חובה אחרת לפי חוק הגנת הפרטיות". — [מדריך תיקון 13](https://www.gov.il/BlobFolder/reports/guide_tikon13_professional/he/tikun%2013%20_170825.pdf)
- Direct-mail guideline §15: the registration duty for direct-mail-services databases with over 10,000 people "נותרה על כנה, גם במתכונת המצומצמת של חובת רישום מאגרי המידע לאחר תיקון מס' 13". — [Guideline 2/2017 (updated)]
- DPO duty, s. 17ב1(א): applies to public bodies; to a controller whose database's main purpose is collection for transfer to others with more than 10,000 people; to bodies whose core activity is systematic large-scale monitoring; and to bodies whose core activity is large-scale special-sensitivity processing. Security officer, s. 17ב(א): required for a controller of five databases that must be registered or notified, a public body, or a bank, insurer or credit rater. — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Definitions: "'דיוור ישיר' – פנייה אישית לאדם, בהתבסס על השתייכותו לקבוצת אוכלוסין, שנקבעה על פי אפיון אחד או יותר של בני אדם ששמותיהם כלולים במאגר מידע"; "'שירותי דיוור ישיר' – מתן שירותי דיוור ישיר לאחרים בדרך של העברת רשימות, מדבקות או נתונים בכל אמצעי שהוא". — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- Section 17ד: "לא יעבד בעל שליטה במאגר מידע או מחזיק במאגר מידע, מידע אישי במאגר מידע המשמש לשירותי דיוור ישיר, אלא אם כן הוא רשום במרשם ואחת ממטרותיו הרשומות היא שירותי דיוור." Section 17ה: "לא יעבד ... מידע אישי במאגר מידע המשמש לשירותי דיוור ישיר, אלא אם כן יש בידו רישום המציין את המקור שממנו קיבל כל אוסף נתונים המשמש לצורך מאגר המידע ומועד קבלתו, וכן למי מסר כל אוסף נתונים כאמור." — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Section 17ו(א): "כל פניה בדיוור ישיר תכיל באופן ברור ובולט – (1) ציון כי הפניה היא בדיוור ישיר, בצירוף ציון מספר הרישום של המאגר המשמש לשירותי דיוור ישיר במרשם מאגרי מידע; (2) הודעה על זכותו של מקבל הפניה להימחק מן המאגר כאמור בסעיף קטן (ב); בצירוף המען שאליו יש לפנות לצורך כך; (3) זהותו ומענו של בעל השליטה במאגר המידע שבו מצוי המידע האישי שעל פיו בוצעה הפניה, והמקורות שמהם קיבל בעל השליטה במאגר מידע זה." — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Guideline §19.1.1: "אם הפניה בדיוור ישיר איננה מבוססת על מידע אישי שהגיע ממאגר לשירותי דיוור ישיר – אין חובה לציין את מספר רישום המאגר, אלא רק את זהות השולח והמקורות". — [Guideline 2/2017 (updated)]
- Guideline §13.1: "פניה פרטנית לאדם הנובעת מהקשר הישיר האישי שלו עם הגורם השולח – כלל איננה דיוור ישיר". Guideline §13.3.1.2 lists, as direct mail, an approach to people who "כלל לא היו במגע עם החברה ... והחברה אספה את המידע האישי עליהם ממקורות אחרים". — [Guideline 2/2017 (updated)]
- Guideline §14.3: an approach can fall under both regimes, direct mail under the Privacy Protection Law and spam under Communications Law s. 30א, "ולכן יידרשו לקיים את הוראות שני ההסדרים החקוקים גם יחד". — [Guideline 2/2017 (updated)]
- Amendment 13 repealed s. 17ז. The Authority's "מידע" opinion records that 17ז had applied the direct-mail rules also to "ידיעה על ענייניו הפרטיים" that is not "מידע". — [ס"ח 3287 (s. 23: "סעיף 17ז לחוק העיקרי – בטל")](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf); [note_privacy_tikon13.pdf](https://www.gov.il/BlobFolder/legalinfo/legat_terms2022/he/note_privacy_tikon13.pdf)
- Fines. Breach of 17ו(א): 50 ₪ times the number of people approached, with a possible minimum of 30,000 ₪ (s. 23כו(ג)(1)(ב), (ג)(2)). Not handling a 17ו(ב) deletion demand as required by 17ו(ד): 15,000 ₪ (s. 23כו(ב)(5)). Breach of 17ה: 2 ₪ per person, with a possible minimum of 20,000 ₪ (s. 23כו(ד)(1)(ד), (ד)(3)). — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf); [Guideline 2/2017 (updated) §21]
- Small-business caps (fifth schedule): "'עסק זעיר' – מפר שמחזור העסקאות שלו בשנה שקדמה למועד ההפרה לא עלה על 4 מיליון שקלים חדשים". On request, total fines per category are capped for a micro business at 20,000 ₪, 50,000 ₪ or 70,000 ₪ depending on the category of breach. — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- Civil claim: guideline §22 says s. 31ב creates a civil tort cause of action for breach of chapters ב' and ד', "לרבות אלה הנוגעות לדיוור ישיר". — [Guideline 2/2017 (updated)]

### Inferences
- The ledger holds domain, form URL, status, time and message version, the suppression list holds domain, email and phone, and later there will be consent replies. For records about individuals this is more than "שם, מען ודרכי התקשרות", and status values such as "opted_out", "sent" or "consented" arguably "מלמד ... על מידע אישי נוסף". The exemption in paragraph (2) is therefore unlikely to apply. The ledger should be treated as a database.
- Is Posiblo's message "דיוור ישיר" for individuals? Recipients are chosen because they belong to a group ("Israeli businesses with a website") listed in Posiblo's database, and they have no prior relationship with Posiblo. That fits the definition and guideline §13.3.1.2. The current template already behaves as direct mail ("פנייה בדיוור ישיר", source, deletion right). Keep it that way. For corporations the definition does not apply, because "אדם" excludes a corporation, but including the details costs nothing.
- No registration number is needed, because the data does not come from a registered direct-mail-services database (guideline §19.1.1).
- 17ה does not legally bind Posiblo, since it is not providing direct-mail services. Posiblo still has to name "המקורות" in each message under 17ו(א)(3), so recording per-site source and time (the URL list's origin and the page the contact detail came from) is good practice and helps prove compliance.

### Gaps
- No Authority text was found that applies the post-amendment database definition to a log or ledger of mostly business records.
- I did not verify whether any 2025–2026 regulations exempt types of databases from s. 8א(ב). I did not find any.

---

## C4. Do the Data Security Regulations 2017 apply? Which security level? What is minimally required for a small database run by one person?

### Takeaway
**Yes.** The regulations apply to any "מאגר מידע", and they keep applying after amendment 13 even where registration is not required. Posiblo fits **"מאגר המנוהל בידי יחיד"** (database managed by an individual): a sole proprietor or a one-owner company, at most two other authorized users, under 10,000 people, not mainly for transfer to others, no professional secrecy. That is the lightest regime. Only regulations 1, 2, 6(א), 9(א), 11(א), 12–14 and 20 apply.

### Cited Findings
- Reg. 1: "'מאגר המנוהל בידי יחיד' – מאגר מידע שמנהל יחיד או תאגיד בבעלות יחיד, ואשר רק היחיד ולכל היותר שני בעלי הרשאה נוספים רשאים לעשות בו שימוש ובאפשרותם לעשות בו שימוש, ולמעט מאגרי מידע כמפורט להלן: (1) מאגר מידע שמטרתו העיקרית היא איסוף מידע לצורך מסירתו לאחר כדרך עיסוק, לרבות שירותי דיוור ישיר; (2) מאגר מידע שיש בו מידע על אודות 10,000 אנשים ומעלה; (3) מאגר מידע הכולל מידע שבעל המאגר כפוף בשלו לחובת סודיות מקצועית לפי דין או לפי עקרונות של אתיקה מקצועית". — [Wikisource regs](https://he.wikisource.org/wiki/%D7%AA%D7%A7%D7%A0%D7%95%D7%AA_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_(%D7%90%D7%91%D7%98%D7%97%D7%AA_%D7%9E%D7%99%D7%93%D7%A2))
- Reg. 21(4): "על מאגר המנוהל בידי יחיד – יחולו תקנות 1, 2, 6(א), 9(א), 11(א), 12 עד 14 ו־20." For comparison, the basic level (reg. 21(3)) also requires a security procedure (reg. 4), mapping and risk review (reg. 5), personnel (reg. 7), access management (reg. 8), outsourcing (reg. 15), security-data retention (reg. 17) and more. — [Wikisource regs](https://he.wikisource.org/wiki/%D7%AA%D7%A7%D7%A0%D7%95%D7%AA_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_(%D7%90%D7%91%D7%98%D7%97%D7%AA_%D7%9E%D7%99%D7%93%D7%A2))
- Requirements that apply to an individual-managed database (Wikisource regs):
  - Reg. 2(א), database definitions document (מסמך הגדרות מאגר) covering at least: "(1) תיאור כללי של פעולות האיסוף והשימוש במידע; (2) תיאור מטרות השימוש במידע; (3) סוגי המידע השונים ...; (4) פרטים על העברת מאגר המידע ... אל מחוץ לגבולות המדינה ...; (5) פעולות עיבוד מידע באמצעות מחזיק; (6) הסיכונים העיקריים של פגיעה באבטחת המידע, ואופן ההתמודדות עמם; (7) שמו של מנהל מאגר המידע, של מחזיק המאגר ושל הממונה על אבטחת מידע בו, אם מונה כזה."
  - Reg. 2(ב): update the document on significant change, and review the need to update it "בכל שנה עד 31 בדצמבר".
  - Reg. 2(ג): "בעל מאגר מידע יבחן, אחת לשנה, אם אין המידע שהוא שומר במאגר רב מן הנדרש למטרות המאגר."
  - Reg. 6(א): systems kept "במקום מוגן, המונע חדירה וכניסה אליו בלא הרשאה".
  - Reg. 9(א): "אמצעים מקובלים ... כדי לוודא כי הגישה למאגר ולמערכות המאגר נעשית בידי בעל הרשאה המורשה לכך בלבד".
  - Reg. 11(א): document every security incident, "ככל האפשר יבוסס התיעוד האמור על רישום אוטומטי".
  - Reg. 12: limit portable devices, and "יראו שימוש בשיטות הצפנה מקובלות כנקיטת אמצעים סבירים להגנה".
  - Reg. 13: proper operation; separate the database systems from other systems as far as reasonable; apply regular updates; do not use systems whose maker no longer supports their security, unless suitably mitigated.
  - Reg. 14: no internet connection "בלא התקנת אמצעי הגנה מתאימים"; "העברת מידע ממאגר המידע, ברשת ציבורית או באינטרנט, תיעשה תוך שימוש בשיטות הצפנה מקובלות"; remote access needs measures that identify the caller and verify authorization.
  — [Wikisource regs](https://he.wikisource.org/wiki/%D7%AA%D7%A7%D7%A0%D7%95%D7%AA_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_(%D7%90%D7%91%D7%98%D7%97%D7%AA_%D7%9E%D7%99%D7%93%D7%A2))
- Statute s. 17(א): "בעל שליטה במאגר מידע ומחזיק במאגר מידע, כל אחד מהם אחראי לאבטחת המידע שבמאגר המידע." — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Breaches of the security regulations carry administrative fines under s. 23כו(ח) and the third schedule. — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)

### Inferences
- Posiblo is run by one person and holds roughly 190 sites. It is not a direct-mail-services database, and no professional secrecy applies. So "מאגר המנוהל בידי יחיד" applies, provided no more than two other people (for example a contractor or an accountant) can access the ledger, logs or backups.
- Exclusion (1) covers databases whose main purpose is transfer to others, "לרבות שירותי דיוור ישיר". Posiblo does its own direct mail and transfers nothing, so the exclusion does not apply.
- Any cloud backup or hosted mail provider that stores the data would be a "מחזיק" ("גורם חיצוני לבעל השליטה במאגר המידע המעבד בעבורו מידע", per ס"ח 3287). Under reg. 2(א)(4)–(5) such providers, and any storage outside Israel, must be listed in the definitions document. Reg. 15 (outsourcing) is not on the reg. 21(4) list.

### Gaps
- I did not verify whether the regulations' wording was amended in 2024–2026 to align with amendment 13 terms. Wikisource still shows "בעל מאגר" and "הרשם". If they were amended, the reg. 21(4) list could have changed.
- No Authority guidance specifically for one-person databases was located. There is an Authority guide on information life cycle for DPOs, cited in D7.

---

## C5. Is a list of website addresses generated by an AI assistant a lawful "source"? Must the message state the source more precisely? Comparison with bought lists, directories, search results, public registries

### Takeaway
Verdict: **GRAY, leaning OK** for the AI-generated URL list. It holds only business website addresses, which for corporations are not personal data. It was not copied from a database in breach of purpose or secrecy, and the personal data itself (email or phone) is taken from the business's own public site. The real legal "source" of the personal data on which the approach is based is therefore the business's own website. To satisfy 17ו(א)(3) "המקורות" fully, the message should name both: that the site was found in a list of Israeli business websites compiled with an AI tool, and that the contact details came from that business's own public site (ideally naming the domain). Bought lists carry the most risk. Public registries carry the least registration burden, but other duties remain.

### Cited Findings
- Guideline §5: the opt-out model "תתאפשר רק אם עצם הכללתו של אדם במאגר לא נעשתה אגב הפרה אחרת של החוק מלכתחילה; כך למשל שימוש במאגר לדיוור ישיר ברשימת שמות שהועתקה שלא כדין ממאגר אחר בניגוד למטרת הקמתו, או שהתקבלה תוך הפרת חובת סודיות – אינו מתרפא באמצעות הסדר ה-Opt-out בדיעבד." — [Guideline 2/2017 (updated)]
- Section 8(ד)(2): "נמסר מידע אישי לבעל שליטה במאגר מידע מגורם אחר, ובעל השליטה לא ידע ולא היה עליו לדעת כי אותו גורם פעל שלא כדין, לא יישא בעל השליטה במאגר המידע באחריות לפי סעיף קטן זה לעיבוד מידע אישי שבוצע לפני שידע או שהיה עליו לדעת כאמור." — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- Guideline §12: "הליבה של סימן ב' בפרק ב' לחוק היא זכותו של נמען הדיוור לדעת מנין קיבל המדוור את המידע האישי עליו, ולבקש את מחיקתו מן המאגר". §12.1 requires keeping source details "כדי שהנמען יוכל לממש את זכותו לבקש את מחיקתו מכל אותם מאגרים שסיפקו את הפרטים עליו". — [Guideline 2/2017 (updated)]
- Guideline §19.1.4: 17ו(א) applies to every direct-mail approach, "לרבות החובה לציין בפני הנמען את המקור ממנו הגיע את המידע", because "ייתכן שהנמען איננו זוכר או שלא ידוע לו כיצד הגיע המידע האישי אודותיו למאגר". — [Guideline 2/2017 (updated)]
- Directories and terms of use (Authority draft, AI context). Footnote 25: if a person publishes on a site with a defined purpose, "ניתן לייחס לו הסכמה לשימוש במידע רק למטרה המוגדרת כאמור, וזאת גם אם תנאי השימוש באתר לא אוסרים במפורש מטרה אחרת". Footnote 26: scraping contrary to terms of use may breach s. 8(ג) and may amount to an offence under s. 23נה. — [AI draft 2025](https://www.gov.il/BlobFolder/rfp/ai_reg/he/ai%20regu_draft.pdf)
- Same draft, footnote 24, cites the "Concluding joint statement on data scraping and the protection of privacy" of October 2024 by a group of data-protection authorities. In §10 it states that controllers of sites that allow sharing personal data must take measures against unlawful scraping, and that unlawful scraping from a database is "אירוע אבטחה חמור". — [AI draft 2025](https://www.gov.il/BlobFolder/rfp/ai_reg/he/ai%20regu_draft.pdf)
- Public registries: s. 8א(ג) exempts from registration or notice only "מאגר שאין בו אלא מידע שפורסם לרבים על פי סמכות כדין או שהועמד לעיון הרבים על פי סמכות כדין". — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- Bought lists from a direct-mail-services provider: the provider's database must be registered (s. 8א(א)(1)(א), 17ד) and keep source records (17ה), and messages based on it must state its registration number (17ו(א)(1); guideline §19.1.1). — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf); [Guideline 2/2017 (updated)]

### Inferences
- AI-generated URL list: the URLs are not "copied unlawfully from another database" or obtained in breach of secrecy, so guideline §5 is not triggered on the known facts. Whether the AI model itself was trained on lawfully collected data is unknowable to Posiblo, and s. 8(ד)(2) (no knowledge, no reason to know) gives a defence for that. Since the list holds no personal data beyond what is on the businesses' own sites, this risk appears low.
- Comparison, ranked from lowest to highest risk:
  1. Public registry (for example a registry published by law): no s. 8א duty, but all other duties apply, and registry-specific terms were not researched.
  2. The business's own site, or search-result URLs leading to it: the same position as Posiblo's current design.
  3. Business directory: purpose limitation (s. 2(9), footnote 25) and the directory's terms of use (s. 8(ג) per the Authority draft) create additional risk. The source sentence must name the directory.
  4. Bought list: the risk that the seller acted unlawfully (8(ד)(1), guideline §5). Seller's registration, the registration number in messages and source records are needed. Highest risk.
- Recording the source is cheap: store per-site "url_list_origin" (the AI-assisted list with a version or date) and "contact_source_url" (the exact page the email or form was taken from). This also allows a precise answer if a recipient asks where their details came from.

### Gaps
- No Authority text or ruling addresses AI-generated lead lists, or lists built from search results, as a "source" under 17ו(א)(3).
- I did not research the terms of specific Israeli public registries (for example the Companies Registrar) or directories.

---

## B9. Is "הפרטים נלקחו מהאתר הציבורי של העסק" sufficient as the source statement under 17ו(א)(3)?

### Takeaway
Verdict: **GRAY, probably sufficient for the contact details themselves, but incomplete.** It names the source of the personal data (the business's own site), which matches the purpose of the rule (guideline §12, §19.1.4). It omits how Posiblo came to hold the site address (an AI-assisted list). A low-cost fix makes the sentence clearly compliant. Proposed wording: "כתובת האתר שלכם נמצאה ברשימת אתרי עסקים בישראל שהוכנה בעזרת כלי בינה מלאכותית, ופרטי הקשר נלקחו מהאתר הציבורי שלכם (‎[domain]‎)."

### Cited Findings
- 17ו(א)(3) requires "זהותו ומענו של בעל השליטה במאגר המידע ... והמקורות שמהם קיבל בעל השליטה במאגר מידע זה". The word is the plural "המקורות". — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Guideline §19.1.3: state "זהותו ומענו של בעל השליטה במאגר המידע בו מצוי המידע האישי על פיו בוצעה הפנייה, והמקורות מהם קיבל בעל השליטה מידע זה". §19.1.4: where the source is the recipient, "רצוי לציין גם את הנסיבות בהן התקבל המידע האישי ממנו". §19.1 requires all details "באופן ברור ובולט ... באופן מצטבר". — [Guideline 2/2017 (updated)]
- Fine for an approach that breaches 17ו(א): 50 ₪ per recipient, with a possible minimum of 30,000 ₪. — [ס"ח 3287, s. 23כו(ג)](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)

### Inferences
- Naming the specific domain in each message is a deterministic per-site string, not personalization of content. Whether it conflicts with the project's "no personalization" rule (CLAUDE.md rule 9) is a design decision for the owner. Without the domain, the sentence still states the type of source.
- 17ו(א)(2) also requires "בצירוף המען שאליו יש לפנות לצורך כך". The current "למחיקה מהרשימה השיבו 'הסר'" together with the email address in the footer probably satisfies this. Stating explicitly "לבקשת מחיקה: [מייל]" removes doubt for form submissions, where "reply" is not possible.

### Gaps
- No Authority example wording or ruling on how specific "המקורות" must be was found.

---

## D4. After "הסר", may Posiblo keep the domain, email or phone on a permanent suppression list, or does that conflict with 17ו(ב)?

### Takeaway
Verdict: **GRAY.** The Authority reads 17ו(ב), for a database used only for direct mail, as "הסרה מוחלטת של פרטי הקשר וכל נתון אחר". It also accepts keeping data where the controller has a legal duty or right to keep it (for example defence against claims), provided every other use stops and access is restricted. No Authority position specifically on suppression lists was found. Keeping a minimal "do not contact" marker solely to prevent re-sending is defensible: Communications Law 30א forbids sending after a refusal, and Posiblo needs to defend against claims. The marker should be minimal, separate, used only for blocking, and disclosed to the requester. For corporations, 17ו does not apply at all ("אדם" excludes a corporation).

### Cited Findings
- 17ו(ב): "כל אדם זכאי לדרוש, בכתב, מבעל השליטה במאגר מידע המשמש לדיוור ישיר, שמידע אישי המתייחס אליו יימחק ממאגר המידע." 17ו(ד): the controller "יפעל ... בהתאם לדרישה ויודיע לאדם, בכתב, כי פעל על פיה". 17ו(ה): if the controller has not notified within 30 days, the person may go to the magistrate's court. — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Guideline §19.3: "במאגר שמטרתו אך ורק משלוח פניות בדיוור ישיר לאנשים הכלולים בו, משמעותה של חובת המחיקה היא כפשוטה: הסרה מוחלטת של פרטי הקשר וכל נתון אחר אודות מבקש המחיקה. אולם, ... כאשר לבעל השליטה במאגר יש חובה או זכות לשמור את המידע האישי על הנמען בעטיין – לא יוכל הנמען לדרוש מחיקה של נתונים אודותיו אשר דרושים למימוש המטרות הלגיטימיות הנוספות של המאגר". Footnote 14 gives examples, including client records kept "לצורכי רשויות המס או התגוננות מתביעות אפשריות". — [Guideline 2/2017 (updated)]
- Guideline footnote 17: "גם אם לבעל השליטה במאגר מטרה לגיטימית להמשיך ולשמור מידע אישי על אדם המבקש מחיקה, כגון הצורך להתגונן מתביעות עתידיות – הרי שעם קבלת בקשת המחיקה על בעל השליטה במאגר להפסיק ולעשות במידע האישי כל שימוש וכל עיבוד אחר שאינו חיוני להגשמת אותה מטרה, ובהתאם גם להגביל את הרשאות הגישה למידע." — [Guideline 2/2017 (updated)]
- Guideline §19.8: a written demand includes "דרישה במסר אלקטרוני כגון דואר אלקטרוני, SMS או צ'אט". "במידת האפשר רצוי לשלוח למבקש אסמכתא מתאימה על בקשת המחיקה". §19.9: the reasonable time frame is "30 ימים". — [Guideline 2/2017 (updated)]
- Fine for not handling a deletion demand: 15,000 ₪ (s. 23כו(ב)(5)). — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf); [Guideline 2/2017 (updated) §21.2]
- "אדם" for s. 17ו excludes a corporation. — [Wikisource consolidated law, s. 3](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)

### Inferences
- The legal "duty or right" that justifies keeping a marker is the refusal mechanism under Communications Law s. 30א(ד) and the statutory-damages exposure for sending after a refusal. Both are covered by the parallel research on 30א, not verified here. Guideline §14.3 confirms both regimes apply together.
- Practical design that follows footnote 17:
  1. On "הסר", delete the ledger row's other data: form URL, status history and message text for that person.
  2. Keep only a one-way hash of the normalized domain, email and phone, plus the date of the request, in a separate suppression table used solely by the pre-send check.
  3. Restrict access to that table.
  4. Within 30 days, confirm to the requester in writing that the data was deleted and that only a minimal blocking marker is kept so they are never contacted again.
- A hash of an email is probably still personal data, because the person is identifiable "במאמץ סביר" by hashing a known address. Hashing therefore lowers exposure but does not take the list outside the law. This is my inference; no source was found.
- An alternative that is closer to the literal text: ask the requester whether they want full deletion, explaining that full deletion means Posiblo cannot guarantee it will not contact them again.

### Gaps
- No Authority opinion, FAQ or ruling on suppression or "do-not-contact" lists under 17ו(ב) was found.
- Whether a hashed suppression entry is "מידע אישי" under the post-amendment definition has no source.

---

## D7. Retention: how long may the ledger, logs and backups be kept?

### Takeaway
Verdict: **UNKNOWN as to a fixed period. No statutory retention period for this kind of data was found in the Privacy Protection Law or the Data Security Regulations.** The binding rules are purpose limitation (s. 8(ב)), the annual excess-data review (reg. 2(ג)) and the Authority's position that data may be kept for a legitimate purpose such as defending claims, but only for that purpose. A defensible policy: keep minimal proof-of-send and proof-of-consent records for as long as claims could be brought, delete everything else (raw pages, debug logs) quickly, and include backups in the deletions.

### Cited Findings
- Section 8(ב): "לא יעבד אדם מידע אישי במאגר מידע אלא למטרת המאגר שנקבעה לו כדין." — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)
- Reg. 2(ג): "בעל מאגר מידע יבחן, אחת לשנה, אם אין המידע שהוא שומר במאגר רב מן הנדרש למטרות המאגר." This is one of the regulations that applies to an individual-managed database (reg. 21(4)). — [Wikisource regs](https://he.wikisource.org/wiki/%D7%AA%D7%A7%D7%A0%D7%95%D7%AA_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_(%D7%90%D7%91%D7%98%D7%97%D7%AA_%D7%9E%D7%99%D7%93%D7%A2))
- The Authority's information life-cycle guide for DPOs describes the "סיום חיי המידע" stage as including when "המידע האישי (כולו או חלקו) אינו נדרש עוד למטרות שלשמן נאסף". At that stage the organization may delete the data "ממאגרי המידע (לרבות גיבויים)", or minimize and obscure it. — [מדריך הגנת פרטיות במחזור חיי המידע האישי](https://www.gov.il/BlobFolder/guide/tool_box_first_page/he/DPODPODPO.pdf)
- Guideline 2/2017, footnotes 14 and 17: keeping data for "התגוננות מתביעות אפשריות" is a legitimate purpose, but it limits use and access to that purpose. — [Guideline 2/2017 (updated)]
- Consent opinion 2026: where data was collected on the basis of consent, its use "יכול להיעשות רק על יסוד ההסכמה שניתנה למטרה זו" (§8). — [consent opinion 2026](https://www.gov.il/BlobFolder/legalinfo/consent-2026/he/cpncent-2025.pdf)

### Inferences
- Records to keep long-term, each with a stated purpose in the database definitions document:
  1. Per-site send record: domain, channel, date and time, message version, outcome. Purpose: prove one approach only and defend claims.
  2. Consent evidence (the "כן" reply with headers or timestamp). Purpose: prove prior consent under 30א for later mailings, for as long as mailings continue plus the claim period.
  3. Suppression markers. Purpose: honor refusals permanently.
- Short-term only: fetched HTML, raw form payloads, debug logs and dry-run reports containing contact details. Delete after the batch is verified, for example within 30–90 days. This figure is my suggestion; no source sets it.
- Backups follow the same retention rules. Deletions under 17ו(ב) should reach backups, or the backups should expire on a short rotation.
- The relevant civil limitation period (חוק ההתיישנות) and the limitation for Communications Law 30א claims were not verified in this research. A lawyer should confirm the claim period before setting the long-term figure.

### Gaps
- No Authority guidance found that sets retention periods for marketing or outreach records.
- The limitation period for claims under the Privacy Protection Law (s. 31ב) and under Communications Law 30א was not researched here.

---

## Authority position on scraping public personal data (AI guidance, consent opinion Feb 2026) as it applies to collecting business contact details for marketing

### Takeaway
The Authority's published position, in the AI draft of 28.4.2025, treats scraping personal data from the internet without informed consent as a prohibited privacy infringement. Publication alone yields consent for other uses only if the site's terms or purpose do not restrict it and the person did not limit the audience. The Feb 2026 consent opinion is not about scraping as such. It confirms that processing needs consent or legal authority, that implied consent is narrow and tied to purpose, and that silence is not consent. **Applied to Posiblo: GRAY.** A business's own contact page is published so that the public can contact it, which supports implied consent for one business inquiry. Posiblo should not go further: no enrichment or profiling, no scraping from directories or social platforms, no use beyond the single consent request, and respect for terms of use and robots.txt.

### Cited Findings
- AI draft §6.3.5: "גם כריית מידע אישי מרשת האינטרנט (scraping) לצורך עיבודו במערכת בינה מלאכותית, לרבות למטרת אימון האלגוריתם, כרוכה בפגיעה אסורה בפרטיות, אם לא ניתנה לכך הסכמה מדעת של נושא המידע". Public self-publication yields consent "למטרות כלליות נוספות, רק אם תנאי השימוש של האתר לא מייחדים במפורש או במשתמע את השימוש במידע למטרה ספציפית אחרת, וגם זאת רק אם נושא המידע בחר שלא להגביל את סוג המשתמשים המורשים להיחשף למידע". It continues: "לפיכך, גם כאשר אדם מפרסם מידע אודות עצמו ברשת חברתית - לא ניתן יהיה בדרך כלל להסיק מעצם הפרסום הסכמה מדעת לעיבוד המידע אודותיו לצורך" [AI processing]. — [AI draft 2025](https://www.gov.il/BlobFolder/rfp/ai_reg/he/ai%20regu_draft.pdf)
- AI draft §10 ("כריית מידע"): site operators must take "אמצעים נאותים כדי למנוע כריית מידע (scraping) אסורה", based "לכל הפחות מתקנות 9 ו-14 לתקנות אבטחת המידע". Unlawful scraping from their database is "אירוע אבטחה חמור". — [AI draft 2025](https://www.gov.il/BlobFolder/rfp/ai_reg/he/ai%20regu_draft.pdf)
- The draft is labeled "טיוטת הנחיית הרשות להגנת הפרטיות: תחולת הוראות חוק הגנת הפרטיות על מערכות בינה מלאכותית", dated "28 אפריל 2025". The copy on gov.il ([ai regu_draft.pdf](https://www.gov.il/BlobFolder/rfp/ai_reg/he/ai%20regu_draft.pdf)) extracts to the same text as a third-party copy. — [AI draft 2025](https://www.gov.il/BlobFolder/rfp/ai_reg/he/ai%20regu_draft.pdf)
- The consent opinion is dated "25 בפברואר 2026" and titled "גילוי דעת בנושא הסכמה בדיני הגנת הפרטיות". It is not labeled a draft. Guideline 2/2017 footnote 8 refers to a February 2025 draft. Key holdings are quoted under C1 (§3, §9, §42, §44, §46). §49: opt-in is required, in the Authority's view, for direct-mail *services* consent in standard contracts. — [consent opinion 2026](https://www.gov.il/BlobFolder/legalinfo/consent-2026/he/cpncent-2025.pdf)
- Duty-to-notify opinion, footnote 2: collection "ממקורות גלויים" without approaching the subject is "לכאורה" possible, but outside that document's scope. — [notify13.pdf](https://www.gov.il/BlobFolder/legalinfo/duty_to_notify/he/notify13.pdf)

### Inferences
- The scraping statements are framed around AI training and processing, which is a different and much heavier use than reading one business's contact page to send one inquiry. The principles still carry over: purpose of publication, the site's terms, and minimal use.
- Posiblo's AI involvement is limited to producing a URL list. No personal data is fed to an AI system at runtime (project rule 2: no LLM calls), so the AI-specific parts of the draft (training, inference) do not apply to the runtime tool.
- Hard boundary that follows: do not harvest contact details from directories, marketplaces or social networks with defined purposes (footnote 25), and do not bypass anti-scraping measures (§10, s. 8(ג)).

### Gaps
- Whether the AI guidance was finalized in 2025–2026 is unknown, because the gov.il page returned 403.
- No Authority enforcement decision on scraping business contact data was found.

---

## Setup steps Posiblo must take (registration/notice, data security, privacy notice, retention, deletion handling)

### Takeaway
No registration and no notice to the Authority are needed. What is needed is the compliance set for a small database: a database definitions document, minimal security per regs 6(א), 9(א), 11(א), 12–14, an annual review, a privacy and s. 11 notice, a complete 17ו(א) block in every message, a 30-day deletion process with written confirmation, and a written retention policy.

### Cited Findings
- No registration: s. 8א(א)(1). No notice: s. 8א(ב)(1). No DPO: s. 17ב1. No security officer: s. 17ב. — [ס"ח 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf); [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA)
- Other duties still apply without registration. — [מדריך תיקון 13](https://www.gov.il/BlobFolder/reports/guide_tikon13_professional/he/tikun%2013%20_170825.pdf)
- Regulations for an individual-managed database: reg. 21(4). Contents of the definitions document: reg. 2(א). Annual review: reg. 2(ב)–(ג). — [Wikisource regs](https://he.wikisource.org/wiki/%D7%AA%D7%A7%D7%A0%D7%95%D7%AA_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA_(%D7%90%D7%91%D7%98%D7%97%D7%AA_%D7%9E%D7%99%D7%93%D7%A2))
- 17ו(א) contents, deletion within 30 days, written confirmation (17ו(ד)–(ה); guideline §19.8–19.9). — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA); [Guideline 2/2017 (updated)]
- Section 11 notice contents. — [Wikisource consolidated law](https://he.wikisource.org/wiki/%D7%97%D7%95%D7%A7_%D7%94%D7%92%D7%A0%D7%AA_%D7%94%D7%A4%D7%A8%D7%98%D7%99%D7%95%D7%AA); [notify13.pdf](https://www.gov.il/BlobFolder/legalinfo/duty_to_notify/he/notify13.pdf)

### Inferences (the concrete checklist)
1. **Registration or notice:** none. Re-check if any of these changes: the database grows past 10,000 people, Posiblo begins passing data to others, or it stores special-sensitivity data. The source for each threshold is above.
2. **Database definitions document (reg. 2), one page, stored outside git:**
   - what is collected (domain, form URL, published email or phone, status, timestamps, message version, replies, suppression markers);
   - the purposes (one consent request; proof of sending, consent and refusal);
   - data types (no special-sensitivity data);
   - transfers abroad and processors (for example the email provider and cloud backup, with their countries);
   - the main risks and controls;
   - the controller's name.
   Review it every year by 31 December, and check yearly that no excess data is kept (reg. 2(ב)–(ג)).
3. **Security minimum (regs 6(א), 9(א), 11(א), 12–14):**
   - full-disk encryption on the laptop;
   - a strong login, with MFA on email and cloud accounts;
   - the ledger, logs and backups readable only by the owner, with at most two other authorized people;
   - encrypted backups and no unencrypted USB copies;
   - OS and software kept patched;
   - firewall and antimalware enabled;
   - TLS for all transfers;
   - a simple incident log, with automatic logging where possible.
   The repo already git-ignores ledger, logs and data (project rule 8), which fits.
4. **Message (17ו(א)):**
   - "פנייה בדיוור ישיר";
   - the right to deletion, with the exact address to send to (an email address, not only "reply");
   - the controller's identity and address;
   - the sources, using the fuller sentence proposed under B9.
   No registration number is needed (guideline §19.1.1).
5. **Section 11 and privacy notice:** add one line or a link to a short privacy notice. It should state:
   - that replying is voluntary;
   - that the purpose is recording consent or refusal;
   - that no data is passed to others;
   - the controller's name and contact;
   - the rights of access and correction (s. 13–14).
   This removes the GRAY item in C1 at low cost. It needs an owner decision because project rule 9 restricts links.
6. **Deletion handling:**
   - accept "הסר" by any written channel (email, SMS, chat; guideline §19.8);
   - act and confirm in writing within 30 days (17ו(ד)–(ה));
   - delete all data except a minimal, access-restricted suppression marker (D4), and explain this in the confirmation.
7. **Retention policy (written):**
   - keep long-term only the per-site send record, consent evidence and suppression markers, with their purposes;
   - delete raw fetched pages, payload dumps and dry-run reports with contact details within a short fixed period;
   - apply the same rules to backups;
   - review yearly (reg. 2(ג)). The long-term period depends on claim limitation periods, which a lawyer should confirm.
8. **Source records:** for each site, store where the URL came from (the AI-assisted list version or date) and the exact page the contact detail was taken from. This supports 17ו(א)(3) and guideline §12.1.

### Gaps
- Whether the Data Security Regulations' wording changed after amendment 13 was not verified.
- No Authority template for a small-business privacy notice was found in this research.
