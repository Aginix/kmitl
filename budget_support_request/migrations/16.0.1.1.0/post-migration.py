"""`date` was relabelled "Date" → "วันที่ส่งคำขอ". ``-u`` loads th.po without
overwrite, so the old th_TH label ("วันที่") would stay; drop it so th.po
fills the new one during this same update."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_fields
           SET field_description = field_description - 'th_TH'
         WHERE model = 'budget.support.request' AND name = 'date'
        """
    )
