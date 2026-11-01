==========================
Web View Origin Inspector
==========================

Find where a button or field of a view comes from, without grepping the code.

**Inspect** (debug mode, users allowed to edit views)

#. Open the form / list, then debug menu (bug icon) → *Inspect View Element*.
#. Hover: the element under the mouse is outlined. Click a button, a field,
   a list column or a field label. *Esc* cancels.
#. The dialog lists every occurrence of that element in the combined view and,
   for each, the views in the order they were applied:

   * *Declared* / *Added*: the view that put the element there;
   * *Attributes changed*: old → new value (``invisible``, ``attrs``,
     ``groups``, ``string``...);
   * *Moved* / *Removed*.

   Each view shows its external ID, module, priority and source file.
#. Actions per occurrence:

   * *Copy XPath*;
   * *Copy Hide XML*: a ``<record>`` hiding the element, to paste in a module,
     with the modules it should depend on;
   * *Hide Now*: creates the extension view in the database (priority 9999,
     applied last) and reloads.

Only elements of the view's own arch are found. Sub-views loaded separately
(a one2many without an inline ``<tree>``) and widgets rendered by JavaScript
are not.

**View Change Log** (Settings → Technical → User Interface)

Every view created, modified (arch, active, priority, inheritance) or deleted
from the database — *Edit View*, *Hide Now*, website editor... — is logged with
the user, a diff, and the XML to port. Changes made by module install, upgrade
or uninstall are not logged.

*Overwritten on Upgrade* flags edits of module views without ``noupdate``: the
next upgrade of that module resets them. Before each deploy, port the
*To Port* entries to code and mark them *Ported to Code*; *Revert* drops a view
created by *Hide Now*.

Install explicitly: ``-i web_view_origin_inspector``.
