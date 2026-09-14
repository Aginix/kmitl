from odoo.addons.purchase_request_dashboard.controllers import main as dashboard_main

# Insert the sent state between to_approve (seq=40) and in_egp (seq=45).
# This runs at module import time, before any HTTP request is handled.
dashboard_main._EXTRA_SUMMARY_STATES.append(
    (42, "sent", "รอพิจารณาให้จัดหา")
)
