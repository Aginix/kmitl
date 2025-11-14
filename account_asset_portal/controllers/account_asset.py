from odoo import http
from odoo.http import request

from odoo.addons.portal.controllers import portal


class AccountAsset(portal.CustomerPortal):
    @http.route(['/account_assets/<string:access_uid>'], type='http', auth="public", website=True)
    def work_acceptance_view(self, access_uid, **kw):
        asset = request.env['account.asset'].sudo()

        access = asset.search([('access_uid', '=', access_uid)], limit=1)
        if not access:
            return request.not_found()

        values = {
            "asset": access,
        }
        return request.render("account_asset_portal.portal_account_asset_page", values)
