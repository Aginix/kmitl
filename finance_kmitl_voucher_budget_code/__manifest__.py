{
    "name": "KMITL Finance - Voucher Budget Code",
    "summary": "รหัสงบประมาณ on the payment voucher, required with its core "
    "dimensions before ยืนยันส่งธนาคาร where a source module asks for it",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL/Finance",
    "depends": [
        "finance_kmitl",
    ],
    "data": [
        "views/account_payment_views.xml",
        "report/report_payment_voucher.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
