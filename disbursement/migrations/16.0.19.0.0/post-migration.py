# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Post-migration for 16.0.19.0.0.

The menu and action "Disbursement Requests" (ใบขอเบิก) are relabelled "All
Disbursement Requests" (ใบขอเบิกทั้งหมด) next to the new "My Disbursement
Requests": drop their stale Thai labels so the module's th.po fills them in
(an update keeps existing translations).
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_ui_menu SET name = name - 'th_TH'
        WHERE id = (
            SELECT res_id FROM ir_model_data
            WHERE module = 'disbursement' AND name = 'menu_disbursement_request'
        )
        """
    )
    cr.execute(
        """
        UPDATE ir_act_window SET name = name - 'th_TH'
        WHERE id = (
            SELECT res_id FROM ir_model_data
            WHERE module = 'disbursement' AND name = 'action_disbursement_request'
        )
        """
    )
