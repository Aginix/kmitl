from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Flag ลงนามในใบปะหน้า as the number-issuing verb (ADR-0017).

    The built-in verbs are ``noupdate`` data, so the new ``issues_number`` value
    in sarabun_verb_data.xml never reaches an existing database on upgrade.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    verb = env.ref("agx_sarabun.verb_sign_approve", raise_if_not_found=False)
    if verb:
        verb.issues_number = True
