# Disbursement Work Station: approve_rector

One station of the disbursement route (see `disbursement_wst/CONTEXT.md` for the
vocabulary). The station record, its authorised group, its Todo type and its place in the
standard route are data in this module; installing it adds the station, uninstalling it
removes it.

Code `approve_rector`: the Rector-delegated approver. Must follow `approve_finance`. Completing
it obligates and consumes the budget (`_action_approve_budget`, idempotent), which is why its
button asks for confirmation.
