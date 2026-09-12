# -*- coding: utf-8 -*-
"""Backfill contract rev 0 for every existing confirmed PO.

Runs once at install/upgrade time. New POs created after this module lands get
their rev 0 automatically via ``purchase.order.button_confirm``; this script
catches everything that was already in ``purchase`` or ``done`` state before
the module was installed.

POs still in ``draft``/``sent``/``cancel``/``to approve`` are left alone — they
will get rev 0 when they hit ``button_confirm`` normally.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    POs = env["purchase.order"].search(
        [
            ("state", "in", ["purchase", "done"]),
            ("contract_ids", "=", False),
        ]
    )
    _logger.info(
        "purchase_contract_revision_kmitl: backfilling rev 0 for %s existing POs",
        len(POs),
    )
    for po in POs:
        try:
            po._create_original_contract()
        except Exception:
            _logger.exception(
                "Failed to create rev 0 for PO %s (id=%s) — skipping",
                po.name,
                po.id,
            )
    _logger.info("purchase_contract_revision_kmitl: rev 0 backfill complete")
