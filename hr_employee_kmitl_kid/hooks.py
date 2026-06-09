from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Seed the KID sequence past the values back-filled onto existing employees.

    ``HrEmployee.init`` assigns existing rows ``K00001 .. K0000N`` (N = number
    of pre-existing employees). The sequence created by ``data/ir_sequence.xml``
    starts at 1, so without this the next employee would be assigned ``K00001``
    again and hit the unique constraint. Advance it to ``N + 1``.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    sequence = env.ref(
        "hr_employee_kmitl_kid.sequence_hr_employee_kmitl_kid",
        raise_if_not_found=False,
    )
    if not sequence:
        return
    count = env["hr.employee"].with_context(active_test=False).search_count([])
    sequence.sudo().number_next_actual = count + 1
