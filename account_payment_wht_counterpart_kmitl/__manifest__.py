# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Account Payment — WHT Counterpart Leg",
    "version": "16.0.1.0.0",
    "category": "KMITL/Finance",
    "summary": "Give each withholding-tax line on a payment voucher its own "
    "debit on the payable, so the entry says what cleared the payable",
    "author": "Aginix Technologies, KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "finance_kmitl",
        # ``wht_tax_id`` on a journal item, which is what a line has to carry
        # for this module to give it a leg at all.
        "l10n_th_account_tax",
    ],
    "installable": True,
    "auto_install": False,
}
