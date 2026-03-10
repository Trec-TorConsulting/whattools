## ADDED Requirements

### Requirement: Product Pull from Whatnot
The system SHALL import products from Whatnot including title, description, weight, taxonomy, variants, listings, and media. Products SHALL be mapped to local inventory items via `externalId`.

#### Scenario: Pull all products
- **WHEN** a seller triggers product sync
- **THEN** the system queries Whatnot's `products` endpoint with pagination
- **AND** creates or updates local inventory items for each product
- **AND** imports product variants with SKU and options
- **AND** imports product media (image URLs)

#### Scenario: Product already exists locally
- **WHEN** a product with matching `whatnot_product_id` already exists
- **THEN** the system updates the local item with Whatnot data
- **AND** preserves local-only fields (COGS, notes, local category)

### Requirement: Product Push to Whatnot
The system SHALL allow sellers to create products on Whatnot from their local inventory, including images, taxonomy assignment, and product attributes.

#### Scenario: Push a new product to Whatnot
- **WHEN** a seller selects "Push to Whatnot" on a local inventory item
- **THEN** the system calls `productCreate` with title, description, weight, taxonomy, variant, listing, and media
- **AND** stores the returned Whatnot product ID on the local item

#### Scenario: Update an existing Whatnot product
- **WHEN** a seller updates a Whatnot-linked inventory item and pushes changes
- **THEN** the system calls `productUpdate` with the Whatnot product ID and updated fields

### Requirement: Product Delete Sync
The system SHALL allow sellers to delete products on Whatnot from WhatTools.

#### Scenario: Delete product on Whatnot
- **WHEN** a seller deletes a Whatnot-linked product
- **THEN** the system calls `productDelete` on Whatnot
- **AND** removes the `whatnot_product_id` from the local item

### Requirement: Product Taxonomy Support
The system SHALL allow sellers to browse and assign Whatnot's product taxonomy when creating or updating products.

#### Scenario: Browse taxonomy tree
- **WHEN** a seller opens the taxonomy picker
- **THEN** the system queries `productTaxonomyNodes` and displays the hierarchical category tree

#### Scenario: Get taxonomy attributes
- **WHEN** a seller selects a taxonomy node
- **THEN** the system queries `productAttributes` for that taxonomy and displays available attributes

### Requirement: Product Image Management
The system SHALL support uploading images for products. Images are stored temporarily locally and pushed to Whatnot with the product via `CreateMediaInput`.

#### Scenario: Upload product image
- **WHEN** a seller uploads an image for a product
- **THEN** the system stores the image temporarily in local storage
- **AND** includes the image source URL when creating/updating the product on Whatnot

### Requirement: Product Variant Support
The system SHALL support multiple variants per product with options (e.g., size, color), individual SKUs, media, and inventory levels.

#### Scenario: Create product with variants
- **WHEN** a seller creates a product with variants
- **THEN** the system creates a `ProductVariant` for each variant with options, SKU, and listing
- **AND** each variant has its own inventory level

### Requirement: Bulk Product Operations
The system SHALL support bulk export and import of products using Whatnot's bulk operation API for large inventory management.

#### Scenario: Bulk export products
- **WHEN** a seller initiates a bulk product export
- **THEN** the system calls `bulkOperationRunQuery` with a products query
- **AND** polls for completion
- **AND** downloads and processes the JSONL results

#### Scenario: Bulk import products
- **WHEN** a seller initiates a bulk product import
- **THEN** the system creates a JSONL file with product data
- **AND** uploads via `uploadCreate` and `bulkOperationRunMutation`
- **AND** polls for completion and reports results
