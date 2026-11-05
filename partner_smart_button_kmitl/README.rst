=============================
Partner Smart Buttons (KMITL)
=============================

Adds smart buttons to the contact form that open the documents linked to
the contact (and its child contacts):

* **ใบขอเบิก** — disbursement requests where the contact is a payee on a line
* **สัญญาเงินยืม** — advance payments borrowed by the contact
* **ใบหัก ณ ที่จ่าย** — withholding tax certificates issued to the contact
* **รายงานขอซื้อ/จ้าง** — purchase request approvals (พจ.1) with the contact as vendor
* **ใบตรวจรับ** — work acceptances with the contact as vendor
* **หลักประกัน** — purchase guarantees of the contact

Each button is shown only to users with access to its model and only when
there is at least one record. Counts respect the current user's access
rights, so the badge always matches what the button opens.
