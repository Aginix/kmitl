# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StateLeadtimeReport(models.Model):
    _name = 'state.leadtime.report'
    _description = 'StateLeadtimeReport'
    _auto = False

    res_model   = fields.Char(readonly=True)
    from_state  = fields.Char(readonly=True)
    to_state    = fields.Char(readonly=True)
    avg_minutes = fields.Float(readonly=True)
    min_minutes = fields.Float(readonly=True)
    max_minutes = fields.Float(readonly=True)
    count       = fields.Integer(readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW state_leadtime_report AS (
                SELECT
                    row_number() OVER () AS id,
                    res_model,
                    from_state,
                    to_state,
                    AVG(duration_minutes) AS avg_minutes,
                    MIN(duration_minutes) AS min_minutes,
                    MAX(duration_minutes) AS max_minutes,
                    COUNT(*)              AS count
                FROM state_leadtime_log
                WHERE duration_minutes > 0
                GROUP BY res_model, from_state, to_state
            )
        """)
