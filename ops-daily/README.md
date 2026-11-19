# المطابقة اليومية: منصة حباق ↔ رواء

تشغيل يومي (5 فجراً بتوقيت الرياض):
1. `creds.json` محلي فقط (غير مرفوع): firebase_key, project, platform_email, platform_password, rewaa_email, rewaa_password.
2. `python3 daily.py [YYYY-MM-DD]` — يسحب المنصة ورواء ليوم العمل (أمس افتراضياً)، يصحح تواريخ تقفيلات الليل، ويكتب `out/data_<day>.json`.
3. نقل الفواتير المعلّقة إلى رواء: `rw/ret2.js` (فواتير شراء) و`rw/api2.js` (مصروفات)، وتسجيل ما نُقل في `out/transfers_<day>.json` وتعليم الفاتورة في المنصة (rewaaRef).
4. `python3 daily_pdf.py <day>` — يبني `out/حباق-التقرير-اليومي-<day>.pdf`.
