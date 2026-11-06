# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Stations Configuration",
    "summary": "Seat the disbursement stations with their acts, editable parts "
    "and members on install",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": [
        "disbursement_work_center",
        "disbursement_validation",
        "disbursement_approver_director",
        "disbursement_approver_rector",
        "disbursement_accounting_kmitl",
        "disbursement_finance_kmitl",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
}
