# Pipe into `odoo_sandbox.sh shell <db> <this file>` on a SANDBOX copy only.
# Sets the admin user's password to "admin" so the headless UI check can log in.
env = globals()["env"]  # injected by `odoo shell`
if not env.cr.dbname.startswith("sbx_"):
    raise SystemExit("refusing: %s is not a sandbox db" % env.cr.dbname)
user = env.ref("base.user_admin")
user.password = "admin"
env.cr.commit()
print("SANDBOX_LOGIN=%s SANDBOX_PASSWORD=admin" % user.login)
