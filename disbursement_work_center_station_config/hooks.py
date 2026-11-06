# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import SUPERUSER_ID, Command, api

# Station (xmlid in disbursement_work_center) -> (acts allowed and required,
# editable parts). Acts have no xmlid, so they are found by code.
STATIONS = {
    "station_check": (
        ["disbursement.validate"],
        [
            "disbursement.edit_header",
            "disbursement.edit_lines",
            "disbursement.edit_attachments",
        ],
    ),
    "station_director": (["disbursement.approve_director"], []),
    "station_rector": (["disbursement.approve_rector"], []),
    "station_bill": (
        ["disbursement.create_bill"],
        ["disbursement.edit_dimensions", "disbursement.edit_lines"],
    ),
    "station_audit": (["disbursement.audit_payment"], ["disbursement.edit_lines"]),
    "station_authorize": (["disbursement.authorize_payment"], []),
}


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Act = env["work.center.act"]
    # The acts are otherwise reflected only once every module has loaded,
    # after this hook: on a fresh install they would not exist yet.
    Act._reflect_acts()
    admin = env.ref("base.user_admin")
    for xmlid, (act_codes, edit_codes) in STATIONS.items():
        acts = Act.search([("code", "in", act_codes)])
        edits = Act.search([("code", "in", edit_codes)])
        env.ref("disbursement_work_center." + xmlid).write(
            {
                "allowed_act_ids": [Command.set(acts.ids)],
                "required_act_ids": [Command.set(acts.ids)],
                "allowed_edit_ids": [Command.set(edits.ids)],
                "member_ids": [Command.link(admin.id)],
            }
        )
