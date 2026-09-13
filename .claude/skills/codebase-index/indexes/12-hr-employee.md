# 12-hr-employee
> 50+ modules | Human resources and employee management system

## Module Map

### aginix_hrms_base/ (application)
- **Purpose**: Core HRMS foundation for KMITL
- **Depends**: hr, mail, contacts
- **Models**:
  - `hr.employee` → Extended employee model
    - Key fields: employee_code, academic_department, position_level
    - Key methods: Custom HR methods
- **Views**: employee_views.xml

### hr_recruitment_kmitl/ (extension)
- **Purpose**: Recruitment customizations for KMITL
- **Depends**: hr_recruitment, aginix_hrms_base
- **Models**: Extended recruitment features
- **Views**: Recruitment views

### hr_employee_* (multiple extensions)
- **Purpose**: Various employee field extensions
- **Depends**: aginix_hrms_base
- **Models**: Additional employee fields (academic standing, attachments, background verification, etc.)
- **Views**: Extended employee forms

### hr_holidays_* (extensions)
- **Purpose**: Leave and holiday management
- **Depends**: hr_holidays, aginix_hrms_base
- **Models**: Leave customizations
- **Views**: Holiday views

### hr_department_* (extensions)
- **Purpose**: Department management enhancements
- **Depends**: hr, aginix_hrms_base
- **Models**: Department extensions
- **Views**: Department views

### hr_employee_management_record/ (extension)
- **Purpose**: Employee management record tracking
- **Depends**: aginix_hrms_base
- **Models**: Management history
- **Views**: Record views

### hr_employee_training_history_kmitl/ (extension)
- **Purpose**: Training history tracking
- **Depends**: aginix_hrms_base
- **Models**: Training records
- **Views**: Training views

### hr_employee_work_email_unique/ (extension)
- **Purpose**: Unique work email validation
- **Depends**: aginix_hrms_base
- **Models**: Email uniqueness constraints
- **Views**: None

### hr_employee_security_role/ (extension)
- **Purpose**: Security role management for employees
- **Depends**: aginix_hrms_base
- **Models**: Role assignments
- **Views**: Security views

### hr_employee_th_id_validation/ (extension)
- **Purpose**: Thai ID validation for employees
- **Depends**: aginix_hrms_base
- **Models**: ID validation logic
- **Views**: ID input validation

### hr_study_leave_kmitl/ (extension)
- **Purpose**: Study leave management
- **Depends**: aginix_hrms_base, hr_holidays
- **Models**: Study leave tracking
- **Views**: Study leave views
