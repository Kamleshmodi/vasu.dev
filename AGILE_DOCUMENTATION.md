# 5. AGILE DOCUMENTATION

Vasu Store utilized a rigorous Agile software development methodology (Scrum framework) to organize a fast-paced, four-month developmental lifecycle. This highly iterative approach allowed the team to pivot rapidly based on continuous testing and refinement.

## Agile Documentation Period

- Start Date: 1 January 2026
- End Date: 20 April 2026

## 5.1 AGILE PROJECT CHARTER

| Charter Category | Detailed Description |
| --- | --- |
| Project Name | Vasu Store - Premium E-Commerce |
| Project Sponsor | L.J. Institute of Computer Applications |
| Mission | To engineer a highly responsive, AI-assisted fashion e-commerce platform that simplifies product discovery and streamlines the digital purchasing journey. |
| Scope | Secure user authentication, hierarchical product catalog, dynamic variant management, persistent cart logic, checkout pipeline, and AI chatbot integration within a Django/SQLite stack. |

## 5.2 AGILE ROAD MAP

The sixteen-week timeline was segmented into four major developmental epochs (Sprints).

| Sprint | Timeline | Core Focus and Objectives |
| --- | --- | --- |
| Sprint 1 | Weeks 1-4 | Django project initialization, database schema design (Products/Variants), and robust User Authentication logic. |
| Sprint 2 | Weeks 5-8 | Comprehensive catalog management, implementation of ProductVariant relationships, and Admin dashboard setup. |
| Sprint 3 | Weeks 9-12 | Frontend HTML/Bootstrap templating, dynamic Cart session management, and Wishlist engineering. |
| Sprint 4 | Weeks 13-16 | Complex AI Chatbot integration, finalized Checkout flow, Security auditing, and production launch. |

## 5.3 AGILE PROJECT PLAN

| Task Name / Deliverable | Allocated Duration | Status |
| --- | --- | --- |
| Requirements & DB Schema Design | 2 Weeks | Complete |
| Configure Django & User Auth Views | 2 Weeks | Complete |
| Build Product Models & Variant Logic | 3 Weeks | Complete |
| Construct Dynamic Cart & Checkout | 3 Weeks | Complete |
| Integrate AI Chatbot Interface | 2 Weeks | Complete |
| UI/UX Polishing with Bootstrap | 2 Weeks | Complete |
| End-to-End System Testing | 2 Weeks | Complete |

## 5.4 AGILE USER STORY

| Story ID | User Story | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| US-01 | As a shopper, I want to register and log in securely so that I can manage my profile and orders. | High | User can sign up, authenticate, and access protected account pages. |
| US-02 | As a shopper, I want to browse products by category and designer so that I can discover items quickly. | High | Category pages load correctly with filterable product listings. |
| US-03 | As a shopper, I want to select size/color variants so that I can buy the exact product option I need. | High | Variant selection updates availability and chosen option in cart. |
| US-04 | As a shopper, I want to add products to cart and wishlist so that I can decide before checkout. | High | Cart/wishlist persist per user session and support quantity updates. |
| US-05 | As a shopper, I want a smooth checkout flow so that I can complete purchases without friction. | High | Shipping details, order summary, and confirmation page work end-to-end. |
| US-06 | As a shopper, I want chatbot-based product help so that I can get recommendations quickly. | Medium | Chatbot returns product-aware responses and graceful fallback replies. |
| US-07 | As an admin/vendor, I want product and order management dashboards so that I can maintain catalog and fulfillment. | Medium | Admin tools support create/update operations and order status workflows. |

## 5.5 AGILE RELEASE PLAN

| Release | Planned Window | Included Features | Outcome |
| --- | --- | --- | --- |
| R1 (Foundation) | End of Week 4 | Core Django setup, authentication, base schema, initial models | Released to internal testing |
| R2 (Catalog Core) | End of Week 8 | Product catalog, variant relations, admin controls | Released to staging |
| R3 (Commerce Flow) | End of Week 12 | Frontend templates, cart, wishlist, preliminary checkout | Released for UAT |
| R4 (Production) | End of Week 16 | AI chatbot, hardened checkout, security hardening, deployment | Released to production |

## 5.6 AGILE SPRINT BACKLOG

| Sprint | Backlog Item | Estimation | Status |
| --- | --- | --- | --- |
| Sprint 1 | Set up project structure and apps | 5 SP | Done |
| Sprint 1 | Implement login, register, and account flows | 8 SP | Done |
| Sprint 1 | Define products and category schema | 8 SP | Done |
| Sprint 2 | Build product CRUD for admin/vendor | 8 SP | Done |
| Sprint 2 | Implement product variants and stock controls | 8 SP | Done |
| Sprint 2 | Create listing and product detail pages | 5 SP | Done |
| Sprint 3 | Build cart session logic and totals | 8 SP | Done |
| Sprint 3 | Add wishlist capabilities | 5 SP | Done |
| Sprint 3 | Complete checkout views/templates | 8 SP | Done |
| Sprint 4 | Integrate AI assistant for product help | 8 SP | Done |
| Sprint 4 | Execute security and validation hardening | 5 SP | Done |
| Sprint 4 | Perform deployment and smoke checks | 5 SP | Done |

## 5.7 AGILE TEST PLAN

| Test Category | Objective | Key Cases | Result |
| --- | --- | --- | --- |
| Unit Testing | Validate model and utility logic | Variant pricing, stock checks, user profile updates | Passed |
| Integration Testing | Verify module interactions | Cart to checkout to order creation flow | Passed |
| Functional Testing | Validate user-facing behavior | Login, browse, variant select, add-to-cart, checkout | Passed |
| API/Service Testing | Validate chatbot and backend integration | Chatbot fallback, product query response format | Passed |
| Security Testing | Ensure secure access and input handling | Auth gating, CSRF handling, form validation | Passed |
| Regression Testing | Prevent feature breakage after changes | Re-run critical flows after each sprint release | Passed |

## 5.8 EARNED-VALUE AND BURN CHARTS

### Earned Value Snapshot

| Metric | Value | Interpretation |
| --- | --- | --- |
| Planned Value (PV) | 100% | Planned completion by Week 16 |
| Earned Value (EV) | 100% | All scoped features delivered |
| Actual Cost (AC) | 100% | Effort aligned with planned capacity |
| Schedule Variance (SV = EV - PV) | 0% | Project delivered on schedule |
| Cost Variance (CV = EV - AC) | 0% | Project delivered within planned effort |

### Sprint Burn-Down Summary

| Sprint | Planned Story Points | Completed Story Points | Remaining at End |
| --- | --- | --- | --- |
| Sprint 1 | 21 | 21 | 0 |
| Sprint 2 | 21 | 21 | 0 |
| Sprint 3 | 21 | 21 | 0 |
| Sprint 4 | 18 | 18 | 0 |

The burn-down trend stayed close to ideal throughout the lifecycle, with backlog closure achieved at the end of each sprint.

## 5.9 COMPLETE PROJECT FUNCTIONALITY LIST

This section lists all major implemented functionalities of the Vasu Store project for documentation and academic reporting.

### A. User Account and Access Management

| Functional Area | Covered Functionality |
| --- | --- |
| Registration | New user registration with validation (password confirmation, email-based account model). |
| Login/Logout | Unified login and logout flow. |
| Password Recovery | Password reset flow (request, reset email sent, token confirmation, reset complete). |
| Role-Based Access | Account roles: Customer, Vendor, Delivery Partner, Admin. |
| Role-Based Redirect | Automatic post-login routing to the appropriate dashboard based on account type. |
| Vendor Profile Bootstrap | Auto-create vendor profile when vendor account logs in first time. |

### B. Product Catalog Architecture

| Functional Area | Covered Functionality |
| --- | --- |
| Dual Catalog Structure | Separate Women and Men catalogs with dedicated models and pages. |
| Category System | Gender-aware hierarchical category management. |
| Designer System | Designer-wise product tagging and listing. |
| Product Core Data | Product name, slug, brand, price, images, availability, category, designer, timestamps. |
| Product Gallery | Multiple gallery images per product. |
| Product Variants | Variant-level size/color/category-type and stock tracking. |
| Category-Type Mapping | Variant category-type synchronization with section models (clothing, footwear, dresses, accessories, bags, beauty where applicable). |
| Slug Management | Unique slug generation and collision handling. |

### C. Women and Men Storefront Features

| Functional Area | Covered Functionality |
| --- | --- |
| Women Pages | Home, New, Designers, Clothing, Dresses, Shoes, Bags, Accessories, Beauty, Sale, Shops, Kendall Editions, Product Detail. |
| Men Pages | Home, New, Designers, Clothing, Shoes, Bags, Accessories, Sale, Happening, Product Detail. |
| Search and Filtering | Text search across product fields; sorting by latest, price low to high, and high to low. |
| Discount Filters | Discount-range based filtering where sale information is available. |
| Dynamic Price Rendering | Original price and discounted display price handling for active sale windows. |

### D. Wishlist and Cart Management

| Functional Area | Covered Functionality |
| --- | --- |
| Wishlist Add/Remove | Add/remove product to wishlist for both catalogs. |
| Wishlist Validation | Duplicate prevention and content-object integrity checks. |
| Cart Add/Remove | Add/remove product to cart for both catalogs. |
| Quantity Management | Increase/decrease cart quantity with stock-limit checks. |
| Cart Cleanup | Auto-remove unavailable/invalid items from cart. |
| Line Total Calculation | Per-item totals and order subtotal calculation using normalized money rounding. |
| Global Counters | Context processor for live cart and wishlist item count in UI. |

### E. Checkout, Address, and Order Placement

| Functional Area | Covered Functionality |
| --- | --- |
| Checkout Screen | Cart summary, subtotal, shipping charge, total payable, payment options. |
| Address Prefill | Auto-prefill checkout address from user profile data. |
| Address Cascade API | Country to state to district to city cascading options endpoint. |
| Postal Validation API | Country/state aware postal code validation endpoint. |
| Delivery Scope Control | Current delivery scope restricted to India with validation rules. |
| Order Payload Validation | Required fields, mobile format, address validation, payment method checks, transaction reference checks. |
| Payment Method Support | Card, UPI, QR Code, and Cash on Delivery. |
| UPI/QR Flow | Dynamic UPI URI and QR generation for checkout and delivery collection contexts. |
| Order Creation | Atomic order creation with order and order-items persistence. |
| Stock Deduction | Transaction-safe stock reduction across variants during order placement. |
| Cart Finalization | Cart cleanup after successful order placement. |

### F. Order, Invoice, and Customer Post-Purchase Features

| Functional Area | Covered Functionality |
| --- | --- |
| Order Tracking Views | Active orders and order history views for user account. |
| Order Context Enrichment | Display status helpers, item links, images, line totals, and rating availability flags. |
| Invoice | Invoice page generation per user order. |
| Rating Workflow | User can rate delivered order items only. |
| Rating Content | Star rating, review title/text, optional review image. |
| Rating Moderation State | Submitted ratings enter pending state until moderated. |

### G. AI and Chatbot Capabilities

| Functional Area | Covered Functionality |
| --- | --- |
| Chatbot Product Search API | Query understanding and catalog search over women and men products. |
| Query Normalization | Stop-word removal, text cleanup, and synonym expansion for better recall. |
| Support Intent Detection | Non-product intents: ordering help, shipping, payment, return/exchange, tracking. |
| Product Serialization | Chatbot returns enriched product cards (name, price, image, link, brand, category, sizes). |
| AI Optionality | OpenAI-assisted response only when enabled via settings. |
| Safe Fallback Replies | Rule-based fallback replies when AI is disabled/unavailable. |

### H. Vendor Backoffice Features

| Functional Area | Covered Functionality |
| --- | --- |
| Vendor Dashboard | Vendor-specific product, sales, and activity overview. |
| Product CRUD | Vendor create/edit/delete product in women or men catalog. |
| Variation Formsets | Multiple variant rows with required validations and minimum stock constraints. |
| Gallery Formsets | Multi-image product gallery management in backoffice. |
| Sale Management | Enable/disable sale per product with discount and date-range controls. |
| Sale Logic | Auto sale price calculation and handling for scheduled/live/ended sales. |
| Product-Category Sync | Automatic sync of section tables from variants during product upsert. |
| Vendor Order Dashboard | Vendor-level order item management. |
| Vendor Payment Dashboard | Vendor-focused payment visibility and payment state tracking. |

### I. Delivery Partner Features

| Functional Area | Covered Functionality |
| --- | --- |
| Delivery Dashboard | Delivery-partner specific assigned orders view. |
| Payment Collection | Delivery-side payment collection update workflow. |
| Delivery Assignment Visibility | Orders show assigned partner and assignment timeline details. |

### J. Admin Control Center Features

| Functional Area | Covered Functionality |
| --- | --- |
| Admin Dashboard | Unified control center with account, order, product, and rating supervision tools. |
| Role Management | Update account role (customer/vendor/delivery/admin) from admin panel. |
| Order Management | Admin order management dashboard with filtering and status controls. |
| Delivery Partner Assignment | Assign delivery partner to orders. |
| Payment Record Management | Update payment and account receipt records, notes, references, and status transitions. |
| Mark Delivered | Explicit admin action to mark orders as delivered. |
| Order Item Status Updates | Update fulfillment status at order-item level. |
| Review Moderation | Approve/reject product ratings with moderation metadata. |

### K. Data Model and Business-State Features

| Functional Area | Covered Functionality |
| --- | --- |
| Generic Product Linking | Cart, Wishlist, and OrderItem use generic content type relations for cross-catalog support. |
| Order Lifecycle States | Processing, Shipped, Delivered, Cancelled. |
| Payment Lifecycle States | Pending, Paid, Refund in Process, Refunded, Failed. |
| Receipt Verification States | Not Received, Pending Verification, Received in Account, Failed. |
| Return and Refund States | Return and refund state models with references and timestamps. |
| Audit Timestamps | Created/updated/moderated/assigned/processed timestamps across operational records. |

### L. User Profile and Address Management

| Functional Area | Covered Functionality |
| --- | --- |
| Profile Management | My Account and Edit Profile pages with image upload. |
| Address Fields | Address line 1/2, country, state, district, city, postal code. |
| Profile Validation | Conditional validation: if any address is entered, required dependent fields enforced. |
| Address Catalog Integration | Offline India address catalog usage for state/district/city validation and options. |

### M. Platform, Deployment, and Reliability Features

| Functional Area | Covered Functionality |
| --- | --- |
| Health Endpoints | Health check endpoints available for uptime monitoring. |
| Static/Media Support | Media serving in debug mode and static collection for deployment. |
| Environment-Driven AI Controls | Toggle AI features via environment variables without code change. |
| Migration Utilities | SQLite-to-PostgreSQL migration helper script and dump/load workflow support. |
| Security Defaults | CSRF-safe auth flows, login-required guards, role-gate guards, and validation-first request handling. |

### Summary Statement for Report

Vasu Store implements end-to-end e-commerce functionality covering customer journey (discovery to checkout), role-specific operational backoffice (vendor, delivery, admin), AI-assisted product guidance, and production-ready data/payment/order governance with validation and moderation workflows.
### 5.10 Compliance and Auth Security Completion Status

| Item | Status |
| --- | --- |
| Privacy Policy page | Completed |
| Terms and Conditions (Terms of Service) page | Completed |
| Cookie consent controls (EU-friendly opt-in/opt-out preferences) | Completed |
| Signup and Login flow tested | Completed |
| Email verification flow | Completed |
| Password reset flow | Completed |
| OAuth support (Google when credentials are configured) | Completed |
| Login rate limiting (brute-force prevention) | Completed |

### 5.11 Final Implementation Task Log (Completed)

| Task Group | Implemented Task | Status |
| --- | --- | --- |
| Legal and Compliance | Added dedicated Privacy Policy page and route | Completed |
| Legal and Compliance | Added dedicated Terms of Service page and route | Completed |
| Legal and Compliance | Added dedicated Cookie Policy page and route | Completed |
| Legal and Compliance | Connected legal links in login/footer/checkout templates | Completed |
| Legal and Compliance | Added reusable cookie consent banner component | Completed |
| Legal and Compliance | Added consent actions: Accept All, Reject Optional, Manage Preferences | Completed |
| Legal and Compliance | Added cookie preference modal re-open support via footer link | Completed |
| Auth and Security | Enforced email verification before login | Completed |
| Auth and Security | Added resend verification email flow from login page | Completed |
| Auth and Security | Added password reset pages and route wiring verification | Completed |
| Auth and Security | Added Google OAuth integration entry flow | Completed |
| Auth and Security | Added Google OAuth safe fallback when provider config is missing | Completed |
| Auth and Security | Added brute-force login rate limiting controls | Completed |
| Testing and Validation | Added auth/security test coverage for signup, login, verification, reset, and lockout | Completed |
| Testing and Validation | Executed Django checks and test suite after implementation updates | Completed |
| UI/UX Improvement | Improved login/register toggle reliability using event-based switching | Completed |
| UI/UX Improvement | Added smooth slide transition behavior between login and register views | Completed |
| UI/UX Improvement | Matched resend verification button styling with Google login button style | Completed |
