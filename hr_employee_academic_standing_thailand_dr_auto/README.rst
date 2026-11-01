===================================================
HR Employee Academic Standing Thailand - Dr. Auto
===================================================

Add-on to **HR Employee Academic Standing Thailand** that turns the manual
``title_dr`` (ดร./Dr.) flag into an automatic value.

Without this module, the ดร. flag on the employee form is ticked by hand. With
it installed, the flag is computed and stored from the employee's highest
education level (``education_level_id``): it is set when the highest level is
ปริญญาเอก (the ``hr_employee_education_history.Q01`` record) and cleared
otherwise. The flag can no longer be edited by hand while this module is
installed.

Because the flag drives the academic-standing title prefix in the base module,
"ดร."/"Dr." then follows the employee's education history automatically.

Installing the module recomputes the flag for all employees, so existing PhD
employees keep their "ดร." prefix.
