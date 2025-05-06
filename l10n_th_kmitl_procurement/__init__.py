# -*- coding: utf-8 -*-
from . import models
from odoo import api, SUPERUSER_ID
from odoo.fields import Command


def post_init(cr, registry):
    # This is a placeholder for the post-init method.
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Install the Thai language pack
    th = (
        env["res.lang"].with_context(active_test=False).search([("code", "=", "th_TH")])
    )
    ll = env["base.language.install"].create(
        {"lang_ids": [Command.clear(), Command.link(th.id)]}
    )
    ll.lang_install()

    # Set the default language for the system to Thai
    default_lang = env["ir.default"].browse([1])
    default_lang.json_value = '"th_TH"'

    # Set the default language for all users to Thai
    users = env["res.users"].search([])
    users.lang = "th_TH"


def uninstall_hook(cr, registry):
    # This is a placeholder for the uninstall method.
    env = api.Environment(cr, SUPERUSER_ID, {})

    default_lang = env["ir.default"].browse([1])
    default_lang.json_value = '"en_US"'

    users = env["res.users"].search([])
    users.lang = "en_US"

    rl = env["res.lang"].search([("code", "=", "th_TH")])
    rl.active = False
