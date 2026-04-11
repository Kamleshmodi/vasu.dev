## 3.5 Data Dictionary

The Data Dictionary defines the schema of the SQLite database mapped via Django ORM. Generated on 2026-03-18 08:36:37 from current db.sqlite3.

### Table Name: aapcategory_designer
Description: Category/catalog metadata table. Current rows: 38.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| name | varchar(100) | Not Null | Human-readable name/title | KAMLESH |
| gender | varchar(10) | Not Null | Business data field | men |

### Table Name: aapstore_cart
Description: Core store/e-commerce table. Current rows: 1.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 173 |
| quantity | INTEGER | Not Null | Inventory quantity/count | 1 |
| added_date | datetime | Not Null | Date/time value | 2026-02-22 16:50:38.371871 |
| user_id | bigint | FK -> appaccounts_account.id, Not Null | Reference ID to related record | 8 |
| content_type_id | INTEGER | FK -> django_content_type.id, Not Null | Reference ID to related record | 6 |
| object_id | integer unsigned | Not Null | Reference ID to related record | 33 |

### Table Name: aapstore_gender
Description: Core store/e-commerce table. Current rows: 0.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | - |
| name | varchar(50) | Unique, Not Null | Human-readable name/title | - |
| slug | varchar(50) | Unique, Not Null | URL-friendly unique text | - |

### Table Name: aapstore_order
Description: Core store/e-commerce table. Current rows: 9.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 13 |
| order_id | varchar(100) | Unique, Not Null | Reference ID to related record | 113 |
| full_name | varchar(255) | Not Null | Human-readable name/title | Sachin Nagar |
| mobile | varchar(15) | Not Null | Contact number | 0123456789 |
| address | varchar(500) | Not Null | Address details | xyz |
| city | varchar(100) | Not Null | Business data field | Ahemdabad |
| state | varchar(100) | Not Null | Business data field | Gujarat |
| zip_code | varchar(10) | Not Null | Business data field | 380016 |
| total_price | decimal | Not Null | Monetary value | 52070.68 |
| payment_method | varchar(50) | Not Null | Business data field | qrcode |
| created_at | datetime | Not Null | Record creation timestamp | 2025-10-04 06:26:48.128035 |
| user_id | bigint | FK -> appaccounts_account.id, Not Null | Reference ID to related record | 1 |
| status | varchar(20) | Not Null | Workflow/state indicator | Processing |

### Table Name: aapstore_orderitem
Description: Core store/e-commerce table. Current rows: 15.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 13 |
| price | decimal | Not Null | Monetary value | 51970.68 |
| order_id | bigint | FK -> aapstore_order.id, Not Null | Reference ID to related record | 13 |
| content_type_id | INTEGER | FK -> django_content_type.id, Not Null | Reference ID to related record | 6 |
| object_id | integer unsigned | Not Null | Reference ID to related record | 13 |
| quantity | INTEGER | Not Null | Inventory quantity/count | 1 |

### Table Name: aapstore_product
Description: Core store/e-commerce table. Current rows: 0.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | - |
| product_name | varchar(200) | Unique, Not Null | Human-readable name/title | - |
| brand | varchar(200) | Not Null | Business data field | - |
| slug | varchar(200) | Unique, Not Null | URL-friendly unique text | - |
| description | TEXT | Not Null | Detailed text description | - |
| price | INTEGER | Not Null | Monetary value | - |
| front_image | varchar(100) | Not Null | Image/media file path or URL | - |
| back_image | varchar(100) | Not Null | Image/media file path or URL | - |
| stock | INTEGER | Not Null | Inventory quantity/count | - |
| is_available | bool | Not Null | Boolean status flag | - |
| created_date | datetime | Not Null | Date/time value | - |
| modified_date | datetime | Not Null | Date/time value | - |
| category_id | bigint | FK -> category.id, Not Null | Reference ID to related record | - |
| designer_id | bigint | FK -> aapcategory_designer.id | Reference ID to related record | - |
| gender_id | bigint | FK -> aapstore_gender.id | Reference ID to related record | - |

### Table Name: aapstore_productrating
Description: Core store/e-commerce table. Current rows: 0.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | - |
| object_id | integer unsigned | Not Null | Reference ID to related record | - |
| rating | smallint unsigned | Not Null | Rating/score value | - |
| title | varchar(120) | Not Null | Business data field | - |
| review | TEXT | Not Null | Business data field | - |
| created_at | datetime | Not Null | Record creation timestamp | - |
| updated_at | datetime | Not Null | Record last update timestamp | - |
| content_type_id | INTEGER | FK -> django_content_type.id, Not Null | Reference ID to related record | - |
| order_id | bigint | FK -> aapstore_order.id, Not Null | Reference ID to related record | - |
| order_item_id | bigint | Unique, FK -> aapstore_orderitem.id, Not Null | Reference ID to related record | - |
| user_id | bigint | FK -> appaccounts_account.id, Not Null | Reference ID to related record | - |

### Table Name: aapstore_userprofile
Description: Core store/e-commerce table. Current rows: 3.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| profile_picture | varchar(100) | Nullable | Business data field | userprofile/7422488_h0xAsaK.jpg |
| address_line_1 | varchar(100) | Not Null | Address details | Civil hospital road, Jangirpura |
| address_line_2 | varchar(100) | Not Null | Address details | Ahmdabad |
| city | varchar(20) | Not Null | Business data field | Ahmedabad |
| state | varchar(20) | Not Null | Business data field | Gujarat |
| country | varchar(20) | Not Null | Business data field | India |
| user_id | bigint | Unique, FK -> appaccounts_account.id, Not Null | Reference ID to related record | 1 |

### Table Name: aapstore_variation
Description: Core store/e-commerce table. Current rows: 0.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | - |
| color | varchar(50) | Not Null | Business data field | - |
| size | varchar(50) | Not Null | Business data field | - |
| product_id | bigint | FK -> aapstore_product.id, Not Null | Reference ID to related record | - |
| stock | INTEGER | Not Null | Inventory quantity/count | - |

### Table Name: aapstore_wishlist
Description: Core store/e-commerce table. Current rows: 6.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 53 |
| added_date | datetime | Not Null | Date/time value | 2025-08-27 01:20:38.849111 |
| user_id | bigint | FK -> appaccounts_account.id, Not Null | Reference ID to related record | 1 |
| content_type_id | INTEGER | FK -> django_content_type.id, Not Null | Reference ID to related record | 6 |
| object_id | integer unsigned | Not Null | Reference ID to related record | 18 |

### Table Name: appaccounts_account
Description: Account module table. Current rows: 13.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 12 |
| password | varchar(128) | Not Null | Hashed password value | pbkdf2_sha256$1000000$6AlyXNoScAwCGsR9yzHIoD$DxAC1WFxu2SE7wW6vnED/sFMs0XtUwn6/7JD7mHjm0M= |
| username | varchar(30) | Unique, Not Null | Human-readable name/title | Abcd |
| email | varchar(60) | Unique, Not Null | Email address | abcd@gmail.com |
| date_joined | datetime | Not Null | Date/time value | 2025-07-03 07:24:13.937514 |
| last_login | datetime | Not Null | Business data field | 2026-02-24 09:21:26.198731 |
| is_admin | bool | Not Null | Boolean status flag | 1 |
| is_staff | bool | Not Null | Boolean status flag | 1 |
| is_active | bool | Not Null | Boolean status flag | 1 |
| is_superuser | bool | Not Null | Boolean status flag | 1 |

### Table Name: appaccounts_account_groups
Description: Account module table. Current rows: 0.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | - |
| account_id | bigint | FK -> appaccounts_account.id, Not Null | Reference ID to related record | - |
| group_id | INTEGER | FK -> auth_group.id, Not Null | Reference ID to related record | - |

### Table Name: appaccounts_account_user_permissions
Description: Account module table. Current rows: 164.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| account_id | bigint | FK -> appaccounts_account.id, Not Null | Reference ID to related record | 5 |
| permission_id | INTEGER | FK -> auth_permission.id, Not Null | Reference ID to related record | 1 |

### Table Name: appmens_accessories
Description: Men's catalog table. Current rows: 9.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 5 |
| product_id | bigint | FK -> appmens_newproduct.id, Not Null | Reference ID to related record | 27 |
| color | varchar(50) | Nullable | Business data field | Black |
| size | varchar(50) | Nullable | Business data field | Full Size |

### Table Name: appmens_bags
Description: Men's catalog table. Current rows: 4.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 3 |
| product_id | bigint | FK -> appmens_newproduct.id, Not Null | Reference ID to related record | 6 |
| color | varchar(50) | Nullable | Business data field | Balenciaga Grey |
| size | varchar(50) | Nullable | Business data field | - |

### Table Name: appmens_clothing
Description: Men's catalog table. Current rows: 97.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 5 |
| size | varchar(50) | Not Null | Business data field | S |
| product_id | bigint | FK -> appmens_newproduct.id, Not Null | Reference ID to related record | 3 |
| color | varchar(50) | Nullable | Business data field | Faded Washed Black |

### Table Name: appmens_dresses
Description: Men's catalog table. Current rows: 0.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | - |
| size | varchar(50) | Not Null | Business data field | - |
| product_id | bigint | FK -> appmens_newproduct.id, Not Null | Reference ID to related record | - |
| color | varchar(50) | Nullable | Business data field | - |

### Table Name: appmens_footwear
Description: Men's catalog table. Current rows: 30.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 6 |
| size | varchar(50) | Not Null | Business data field | 6 |
| product_id | bigint | FK -> appmens_newproduct.id, Not Null | Reference ID to related record | 10 |
| color | varchar(50) | Nullable | Business data field | All White |

### Table Name: appmens_happenings
Description: Men's catalog table. Current rows: 9.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| description | TEXT | Not Null | Detailed text description | A Curated Collection Of Noteworthy Releases And Collaborations |
| image | varchar(100) | Not Null | Image/media file path or URL | photos/mens_features/m5e7ycdsgwnh3wtxxxgj.jpeg |
| title | varchar(255) | Not Null | Business data field | Special  Launches |

### Table Name: appmens_hometemplate
Description: Men's catalog table. Current rows: 0.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | - |
| home_template_image | varchar(100) | Not Null | Image/media file path or URL | - |
| product_type | varchar(20) | Not Null | Business data field | - |

### Table Name: appmens_newproduct
Description: Men's catalog table. Current rows: 39.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 3 |
| product_name | varchar(200) | Unique, Not Null | Human-readable name/title | 1981 Painter Decorator Trouser |
| brand | varchar(200) | Not Null | Business data field | BALENCIAGA |
| slug | varchar(200) | Unique, Not Null | URL-friendly unique text | 1981-painter-decorator-trouser |
| designer_id | bigint | FK -> aapcategory_designer.id, Not Null | Reference ID to related record | 1 |
| description | TEXT | Not Null | Detailed text description | Self: 100% cotton.     Contrast Fabric: 100% polyester.       Machine wash.      Elastic waistband with interior drawstring closure.     Side seam pockets.    Midweight brushed french terry fabric  Made in Portugal  Our Style No. BALF-MF39  Manufacturer Style No. 826385TSVH31041  Model is wearing size M. View detailed measurements of this item. |
| price | decimal | Not Null | Monetary value | 86184.71 |
| front_image | varchar(100) | Not Null | Image/media file path or URL | photos/products/agsvsy4gs7obs6l1jrqq.jpeg |
| back_image | varchar(100) | Not Null | Image/media file path or URL | photos/products/hdvcoeoqhkpctdvz4o1m.jpeg |
| is_available | bool | Not Null | Boolean status flag | 1 |
| created_date | datetime | Not Null | Date/time value | 2025-07-13 05:01:01.704560 |
| modified_date | datetime | Not Null | Date/time value | 2025-07-13 12:46:29.366168 |
| category_id | bigint | FK -> category.id, Not Null | Reference ID to related record | 23 |
| gender | varchar(10) | Not Null | Business data field | Mens |

### Table Name: appmens_productvariation
Description: Men's catalog table. Current rows: 122.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| color | varchar(50) | Nullable | Business data field | Faded Washed Black |
| stock | INTEGER | Not Null | Inventory quantity/count | 5 |
| product_id | bigint | FK -> appmens_newproduct.id, Not Null | Reference ID to related record | 3 |
| category_type | varchar(50) | Not Null | Business data field | clothing |
| size | varchar(50) | Nullable | Business data field | 25 |

### Table Name: appmens_saleitems
Description: Men's catalog table. Current rows: 1.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| discount_percentage | REAL | Not Null | Numeric decimal value | 25.0 |
| start_date | date | Not Null | Date/time value | 2025-07-20 |
| end_date | date | Not Null | Date/time value | 2025-07-31 |
| sale_price | decimal | Not Null | Monetary value | 59000 |
| product_id | bigint | FK -> appmens_newproduct.id, Not Null | Reference ID to related record | 33 |

### Table Name: appwomens_accessories
Description: Women's catalog table. Current rows: 2.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| product_id | bigint | FK -> appwomens_newproduct.id, Not Null | Reference ID to related record | 19 |
| color | varchar(50) | Not Null | Business data field | White |
| size | varchar(50) | Nullable | Business data field | One Size |

### Table Name: appwomens_bags
Description: Women's catalog table. Current rows: 3.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| product_id | bigint | FK -> appwomens_newproduct.id, Not Null | Reference ID to related record | 13 |
| color | varchar(50) | Not Null | Business data field | 0 |
| size | varchar(50) | Nullable | Business data field | 0 |

### Table Name: appwomens_beautyproducts
Description: Women's catalog table. Current rows: 1.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| product_id | bigint | FK -> appwomens_newproduct.id, Not Null | Reference ID to related record | 21 |
| color | varchar(50) | Nullable | Business data field | Medium Deep 25 |
| size | varchar(50) | Nullable | Business data field | One Size |

### Table Name: appwomens_clothing
Description: Women's catalog table. Current rows: 8.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 2 |
| size | varchar(50) | Not Null | Business data field | L |
| color | varchar(50) | Not Null | Business data field | Black |
| product_id | bigint | FK -> appwomens_newproduct.id, Not Null | Reference ID to related record | 4 |

### Table Name: appwomens_dresses
Description: Women's catalog table. Current rows: 7.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| size | varchar(50) | Not Null | Business data field | Free Size |
| color | varchar(50) | Not Null | Business data field | Black |
| product_id | bigint | FK -> appwomens_newproduct.id, Not Null | Reference ID to related record | 4 |

### Table Name: appwomens_footwear
Description: Women's catalog table. Current rows: 7.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 4 |
| size | varchar(50) | Not Null | Business data field | 6 |
| color | varchar(50) | Not Null | Business data field | Brun Fonce |
| product_id | bigint | FK -> appwomens_newproduct.id, Not Null | Reference ID to related record | 3 |

### Table Name: appwomens_hometemplate
Description: Women's catalog table. Current rows: 0.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | - |
| product_type | varchar(20) | Not Null | Business data field | - |
| home_template_image | varchar(100) | Not Null | Image/media file path or URL | - |

### Table Name: appwomens_kendalls_editions
Description: Women's catalog table. Current rows: 8.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| edition_name | varchar(200) | Not Null | Human-readable name/title | KENDALL'S EDIT |
| edition_description | TEXT | Not Null | Detailed text description | Shop Kendall's curated edit of the must-have pieces from the designer collections. |
| edition_image | varchar(100) | Not Null | Image/media file path or URL | photos/editions/u52f6x0yhh77db40ldew.jpeg |
| edition_number | varchar(10) | Not Null | Business data field | 01 |

### Table Name: appwomens_newproduct
Description: Women's catalog table. Current rows: 17.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 3 |
| product_name | varchar(200) | Unique, Not Null | Human-readable name/title | Ballet Flat |
| brand | varchar(200) | Not Null | Business data field | ALAIA |
| slug | varchar(200) | Unique, Not Null | URL-friendly unique text | ballet-flat |
| designer_id | bigint | FK -> aapcategory_designer.id, Not Null | Reference ID to related record | 3 |
| price | decimal | Not Null | Monetary value | 99610.47 |
| front_image | varchar(100) | Not Null | Image/media file path or URL | photos/products/ALIA-WZ250_V1_iGxqTkO.jpg |
| is_available | bool | Not Null | Boolean status flag | 1 |
| gender | varchar(10) | Not Null | Business data field | Women |
| created_date | datetime | Not Null | Date/time value | 2025-07-03 17:40:44.972401 |
| modified_date | datetime | Not Null | Date/time value | 2025-10-10 15:29:39.284697 |
| category_id | bigint | FK -> category.id, Not Null | Reference ID to related record | 1 |
| product_description | TEXT | Nullable | Detailed text description | Soft and stylish shoes |
| back_image | varchar(100) | Nullable | Image/media file path or URL | photos/products/ALIA-WZ250_V1_SNWg4AR.jpg |

### Table Name: appwomens_productvariation
Description: Women's catalog table. Current rows: 16.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 16 |
| color | varchar(50) | Nullable | Business data field | Black |
| stock | INTEGER | Not Null | Inventory quantity/count | 1 |
| product_id | bigint | FK -> appwomens_newproduct.id, Not Null | Reference ID to related record | 3 |
| category_type | varchar(50) | Not Null | Business data field | - |
| size | varchar(50) | Nullable | Business data field | 30 |

### Table Name: appwomens_saleitems
Description: Women's catalog table. Current rows: 2.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| discount_percentage | REAL | Not Null | Numeric decimal value | 20.0 |
| start_date | date | Not Null | Date/time value | 2025-07-11 |
| end_date | date | Not Null | Date/time value | 2025-07-15 |
| sale_price | REAL | Not Null | Monetary value | 8000.0 |
| product_id | bigint | FK -> appwomens_newproduct.id, Not Null | Reference ID to related record | 4 |

### Table Name: appwomens_shops
Description: Women's catalog table. Current rows: 6.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 5 |
| product_id | bigint | FK -> appwomens_newproduct.id, Not Null | Reference ID to related record | 3 |
| is_trending | bool | Not Null | Boolean status flag | 0 |
| is_vasu_soap | bool | Not Null | Boolean status flag | 1 |

### Table Name: auth_group
Description: Django authentication/authorization table. Current rows: 0.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | - |
| name | varchar(150) | Unique, Not Null | Human-readable name/title | - |

### Table Name: auth_group_permissions
Description: Django authentication/authorization table. Current rows: 0.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | - |
| group_id | INTEGER | FK -> auth_group.id, Not Null | Reference ID to related record | - |
| permission_id | INTEGER | FK -> auth_permission.id, Not Null | Reference ID to related record | - |

### Table Name: auth_permission
Description: Django authentication/authorization table. Current rows: 172.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| content_type_id | INTEGER | FK -> django_content_type.id, Not Null | Reference ID to related record | 1 |
| codename | varchar(100) | Not Null | Human-readable name/title | add_logentry |
| name | varchar(255) | Not Null | Human-readable name/title | Can add log entry |

### Table Name: category
Description: Category/catalog metadata table. Current rows: 137.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 119 |
| category_name | varchar(50) | Not Null | Human-readable name/title | 100% cow suede |
| slug | varchar(100) | Unique, Not Null | URL-friendly unique text | 100-cow-suede-men |
| description | TEXT | Not Null | Detailed text description | - |
| gender | varchar(10) | Not Null | Business data field | men |

### Table Name: django_admin_log
Description: Django framework system table. Current rows: 485.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| object_id | TEXT | Nullable | Reference ID to related record | 1 |
| object_repr | varchar(200) | Not Null | Business data field | KAMLESH (women) |
| action_flag | smallint unsigned | Not Null | Business data field | 1 |
| change_message | TEXT | Not Null | Business data field | [{"added": {}}] |
| content_type_id | INTEGER | FK -> django_content_type.id | Reference ID to related record | 6 |
| user_id | bigint | FK -> appaccounts_account.id, Not Null | Reference ID to related record | 1 |
| action_time | datetime | Not Null | Date/time value | 2025-07-03 07:45:07.178068 |

### Table Name: django_content_type
Description: Django framework system table. Current rows: 43.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| app_label | varchar(100) | Not Null | Business data field | admin |
| model | varchar(100) | Not Null | Business data field | logentry |

### Table Name: django_migrations
Description: Django framework system table. Current rows: 81.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| id | INTEGER | Primary Key, Not Null | Unique row identifier | 1 |
| app | varchar(255) | Not Null | Business data field | aapcategory |
| name | varchar(255) | Not Null | Human-readable name/title | 0001_initial |
| applied | datetime | Not Null | Business data field | 2025-07-03 07:23:27.439240 |

### Table Name: django_session
Description: Django framework system table. Current rows: 22.

| Field Name | Data Type | Constraint | Description | Sample Data |
|---|---|---|---|---|
| session_key | varchar(40) | Primary Key, Unique, Not Null | Business data field | 1dqoga0xiymbmqom18gs9jazw0kdbstw |
| session_data | TEXT | Not Null | Business data field | .eJxVjMsOwiAQRf-FtSEwlEdduvcbCMwwUjU0Ke3K-O_apAvd3nPOfYmYtrXGrZclTiTOQovT75YTPkrbAd1Tu80S57YuU5a7Ig_a5XWm8rwc7t9BTb1-a1AcPGZgKhDCWAiVyUADscvWORwJnB8ssyIwSjsetU_eENrACKDE-wP2QzgK:1uXLxH:RKZpZCzPkM4yT7e8Y-XEqhqd6ClFIBxfgUv4j9PJCJU |
| expire_date | datetime | Not Null | Date/time value | 2025-07-17 15:34:31.944501 |
