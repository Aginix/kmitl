{
    "name": "KMITL Accounting",
    "version": "16.0.1.0.1",
    "category": "KMITL/Accounting",
    "summary": "งานบัญชี KMITL: ตั้งหนี้, ล้างหนี้, สมุดรายวัน, รายงานบัญชี",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "AGPL-3",
    "depends": [
        "account_operating_unit",
        "base_tier_validation",
        "budget",
        "l10n_th_account_tax",
    ],
    "data": [
        "security/security.xml",
        "views/account_move_views.xml",
        "views/account_payment_method_views.xml",
        "views/menuitem.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
}
