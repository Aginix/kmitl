1. Ensure the **Portal Profile** module is installed and that portal users have
   completed their profiles (name, address, education history, work history,
   skills, etc.).

2. When a logged-in portal user navigates to a job posting and clicks
   **Apply**, the application form is pre-filled with data from their portal
   profile:

   - Thai and English names (first, middle, last)
   - Contact information (email, phone, address)
   - Personal details (birthday, nationality, marital status, spouse info)
   - Emergency contact details
   - Academic position and OCSC exam information
   - Skills (foreign languages, computer skills, other abilities, interests)

3. On form submission, the created ``hr.applicant`` record is also populated
   with the applicant's **education history** and **work history** copied from
   the portal profile.

4. HR staff can review the full applicant profile directly in the backend
   under **Recruitment > Applications**.
