from odoo import http
from odoo.http import request

from odoo.addons.portal.controllers import portal


class AccountAsset(portal.CustomerPortal):
    @http.route(['/account_assets/<string:access_uid>'], type='http', auth="public", website=True)
    def asset_portal_view(self, access_uid, **kw):
        Asset = request.env['account.asset'].sudo()
        access_uid = (access_uid or "").lower()
        asset = Asset.search([('access_uid', '=', access_uid)], limit=1)

        if not asset:
            return request.not_found()

        values = {
            "asset": asset,
        }
        return request.render("account_asset_kmitl.portal_account_asset", values)
