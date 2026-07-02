# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Tier Validation",
    "version": "16.0.1.0.0",
    "summary": "Two-tier sequential approval (Accounting Head -> Finance "
    "Director) for disbursement requests",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "disbursement",
        "base_tier_validation",
        "base_tier_validation_comment",
        "i18n_th_tier_validation",
        "base_user_role",
    ],
    "data": [
        "security/security.xml",
        "data/tier_definition.xml",
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
