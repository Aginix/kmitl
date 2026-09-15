from odoo.addons.purchase_request_dashboard.controllers import main as dashboard_main

# Insert the in_egp state between to_approve (seq=40) and in_approval (seq=50).
# This runs at module import time, before any HTTP request is handled.
dashboard_main._EXTRA_SUMMARY_STATES.append(
    (45, "in_egp", "รอดำเนินการ E-GP")
)
