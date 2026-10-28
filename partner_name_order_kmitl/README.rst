=========================
KMITL Partner Name Order
=========================

Overrides the partner form views from ``partner_middlename`` to:

* Display name parts in the natural reading order
  **First Name → Middle Name → Last Name**
  (upstream order is Middle Name, Last Name, First Name).
* Remove the conditional ``required`` on the middle name field in the view.
  The Python ``_check_name`` constraint from ``partner_middlename`` is left
  untouched, so at least one of first name or last name is still enforced
  when saving.
