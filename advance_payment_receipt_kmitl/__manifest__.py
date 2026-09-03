{
    "name": "Advance Payment - Receipt KMITL Bridge",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL/Accounting",
    "summary": "ออกใบเสร็จรับเงิน (kmitl.receipt) อัตโนมัติเมื่อรับเงินคืนจากสัญญายืมเงิน",
    "depends": [
        # advance_payment_budget (not bare advance_payment) supplies the
        # agreement's analytic_distribution + 4D dimensions, which the receipt
        # needs for its required department_analytic_id.
        "advance_payment_budget",
        "receipt_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/product_data.xml",
        "views/advance_payment_return_line_views.xml",
        "views/advance_payment_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "application": False,
    "installable": True,
    # Optional integration: it replaces the return's inbound account.payment
    # with a real cash receipt, so it is installed deliberately rather than
    # whenever both sides happen to be present (cf. purchase_request_advance_payment).
    "auto_install": False,
    "license": "AGPL-3",
}
