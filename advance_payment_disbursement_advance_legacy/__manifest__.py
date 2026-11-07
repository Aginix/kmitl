# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Advance Payment - Legacy Advance Disbursement Bridge",
    "summary": "แจ้งเจ้าหน้าที่งานเงินยืมเมื่อใบเบิกเงินยืม (ระบบเก่า) ตัดงบประมาณ",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "license": "LGPL-3",
    "depends": [
        "advance_payment",
        "disbursement_advance_legacy",
        "disbursement_budget",
        "mail_activity_todo",
    ],
    "data": ["data/mail_activity_type.xml"],
    "installable": True,
    "auto_install": True,
}
