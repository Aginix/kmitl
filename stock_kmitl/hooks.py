# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
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
