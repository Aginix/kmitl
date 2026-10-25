# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: drop the stored extension views of the request.

This version removes the approval methods and states (the acts moved to their
own modules). Odoo validates the request form, as soon as its file reloads,
together with the extension views still stored from the old version — those of
``disbursement`` itself load from later files — and they still name the removed
``action_return_verification_open_wizard`` and the ``verified`` state, which
fails the upgrade. Every module that extends the request is upgraded in the same
run, so dropping its views lets each one reload them from its own files.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        DELETE FROM ir_ui_view v
        USING ir_model_data d, ir_module_module m
        WHERE d.model = 'ir.ui.view'
          AND d.res_id = v.id
          AND m.name = d.module
          AND m.state IN ('to upgrade', 'to install')
          AND v.model = 'disbursement.request'
          AND v.mode = 'extension'
        """
    )
