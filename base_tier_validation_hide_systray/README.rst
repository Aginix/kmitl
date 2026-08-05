==========================================
Tier Validation — Hide Reviewer Menu Systray
==========================================

Removes the OCA ``base_tier_validation`` "Reviewer Menu" bell from the
systray. Install this in setups where the bell duplicates another
notification surface (e.g. a unified Todo inbox) and needs to go. It
touches no data and adds no Python — one JS service that runs after
``base_tier_validation``'s own systray service and calls ``registry.remove``.
