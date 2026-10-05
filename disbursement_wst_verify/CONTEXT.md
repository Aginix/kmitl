# Disbursement Work Station: verify

One station of the disbursement route (see `disbursement_wst/CONTEXT.md` for the
vocabulary). The station record, its authorised group, its Todo type and its place in the
standard route are data in this module; installing it adds the station, uninstalling it
removes it.

Code `verify`, group `disbursement.group_disbursement_officer`, first on the route.
Widens `under_verification` to "in progress at this station" and, on completion, clears
the return-to-verification markers and the source-correction Todos.
