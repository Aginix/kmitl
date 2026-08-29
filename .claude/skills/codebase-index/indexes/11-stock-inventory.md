# 11-stock-inventory
> 15+ modules | Stock and inventory management system

## Module Map

### stock_kmitl/ (application)
- **Purpose**: Core stock management customizations
- **Depends**: stock, account_analytic_kmitl
- **Models**:
  - `stock.picking` → Extended picking
    - Key fields: analytic_distribution
- **Views**: stock_picking_views.xml

### stock_inventory_kmitl/ (extension)
- **Purpose**: Inventory management enhancements
- **Depends**: stock_kmitl, stock_inventory
- **Models**: Inventory customizations
- **Views**: Inventory views

### stock_inventory_department/ (extension)
- **Purpose**: Department-based inventory restrictions
- **Depends**: stock_inventory_kmitl, hr_department
- **Models**: Department access control
- **Views**: Department inventory views

### stock_inventory_restriction/ (extension)
- **Purpose**: Inventory access restrictions
- **Depends**: stock_inventory_kmitl
- **Models**: Security rules
- **Views**: None

### stock_picking_kmitl/ (extension)
- **Purpose**: Picking operation customizations
- **Depends**: stock_kmitl
- **Models**: Extended picking features
- **Views**: Picking views

### stock_request_kmitl/ (extension)
- **Purpose**: Stock request system
- **Depends**: stock_kmitl, stock_request
- **Models**:
  - `stock.request` → Request model
    - States: draft → approved → done
- **Views**: Request views

### stock_request_kmitl_tier_validation/ (extension)
- **Purpose**: Tier validation for stock requests
- **Depends**: stock_request_kmitl, base_tier_validation
- **Models**: Approval workflow
- **Views**: Validation views

### stock_scrap_kmitl/ (extension)
- **Purpose**: Scrap management customizations
- **Depends**: stock_kmitl, stock_scrap
- **Models**: Extended scrap features
- **Views**: Scrap views

### stock_scrap_attachment/ (extension)
- **Purpose**: Attachment support for scrap operations
- **Depends**: stock_scrap_kmitl
- **Models**: File attachments
- **Views**: Attachment views

### stock_scrap_hide_location_id/ (extension)
- **Purpose**: Hide location fields in scrap
- **Depends**: stock_scrap_kmitl
- **Models**: UI modifications
- **Views**: Modified scrap views

### stock_scrap_origin_readonly_done/ (extension)
- **Purpose**: Make origin readonly when done
- **Depends**: stock_scrap_kmitl
- **Models**: Field readonly logic
- **Views**: None

### stock_scrap_reason_text/ (extension)
- **Purpose**: Text-based scrap reasons
- **Depends**: stock_scrap_kmitl
- **Models**: Reason text fields
- **Views**: Reason input views

### stock_scrap_responsible_user/ (extension)
- **Purpose**: Responsible user tracking for scraps
- **Depends**: stock_scrap_kmitl
- **Models**: User assignment
- **Views**: User selection views

### stock_warehouse_kmitl/ (extension)
- **Purpose**: Warehouse management customizations
- **Depends**: stock_kmitl
- **Models**: Warehouse extensions
- **Views**: Warehouse views

### stock_request_aginix/ (extension)
- **Purpose**: Aginix-specific stock request features
- **Depends**: stock_request_kmitl
- **Models**: Additional features
- **Views**: Enhanced request views
