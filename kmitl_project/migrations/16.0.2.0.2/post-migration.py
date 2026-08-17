# -*- coding: utf-8 -*-
import logging
from collections import defaultdict

from odoo import SUPERUSER_ID, api, fields

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Give the project running-number sequence a separate counter per fiscal
    year: enable ``use_date_range`` so ``next_by_code(sequence_date=fy.date_to)``
    draws from a per-year date range instead of one global counter (which kept
    incrementing across years, only the ``%(year_be)s`` prefix changed).

    Existing keys were minted under the old global counter, so seed each
    calendar-year range (the bucket keyed by the fiscal year's end date) past
    the highest number already issued that year — otherwise the freshly created
    range would restart at 0001 and collide with a live project code.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    seq = env.ref("kmitl_project.kmitl_project_seq", raise_if_not_found=False)
    if not seq:
        return
    seq.use_date_range = True

    # Highest trailing number per calendar-year-of-fiscal-year-end from the keys
    # already issued (key format: PROJ/<year_be>/<NNNN>).
    projects = env["kmitl.project"].search(
        [("key", "!=", False), ("account_fiscal_year_id", "!=", False)]
    )
    max_by_year = defaultdict(int)
    for project in projects:
        year = project.account_fiscal_year_id.date_to.year
        tail = project.key.rsplit("/", 1)[-1]
        if tail.isdigit():
            max_by_year[year] = max(max_by_year[year], int(tail))

    DateRange = env["ir.sequence.date_range"]
    for year, max_num in max_by_year.items():
        date_from = fields.Date.to_date("%d-01-01" % year)
        date_to = fields.Date.to_date("%d-12-31" % year)
        date_range = DateRange.search(
            [
                ("sequence_id", "=", seq.id),
                ("date_from", "=", date_from),
                ("date_to", "=", date_to),
            ],
            limit=1,
        )
        if date_range:
            date_range.number_next = max_num + 1
        else:
            DateRange.create(
                {
                    "sequence_id": seq.id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "number_next": max_num + 1,
                }
            )
        _logger.info(
            "kmitl_project: seeded project sequence range %s at %s",
            year,
            max_num + 1,
        )
