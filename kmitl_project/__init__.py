# -*- coding: utf-8 -*-
from . import controller
from . import models
from . import wizard
from . import report


def _post_init_approval_state(cr, registry):
    cr.execute(
        """
        UPDATE kmitl_project
        SET approval_state = 'approved'
        WHERE state != 'draft'
          AND (approval_state IS NULL OR approval_state = 'draft')
        """
    )
