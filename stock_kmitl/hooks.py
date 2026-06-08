# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    # One-time setup at install: rename the first (oldest) warehouse to KMITL
    # and clear its operating unit. KMITL runs a single warehouse, so only the
    # oldest one is configured here.
    env = api.Environment(cr, SUPERUSER_ID, {})

    warehouse = env["stock.warehouse"].search([], limit=1, order="id asc")
    if warehouse:
        warehouse.write(
            {
                "name": "KMITL",
                "operating_unit_id": False,
                "code": "KMITL",
            }
        )
        _logger.warning("Updated warehouse %s -> KMITL, OU cleared", warehouse.id)
