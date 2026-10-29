from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """shared_group_ids already exists (agx_approval_operating_unit) when this
    module turns it into a computed field, so Odoo does not fill it for the
    requests that already have ใบขอเบิก: compute them here."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    requests = (
        env["approval.request"]
        .with_context(active_test=False)
        .search([("disbursement_request_ids", "!=", False)])
    )
    env.add_to_compute(requests._fields["shared_group_ids"], requests)
    requests.flush_recordset(["shared_group_ids"])
