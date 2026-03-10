"""GraphQL mutations for the Whatnot Seller API."""

# ── Product Mutations ───────────────────────────────────────────────

PRODUCT_CREATE_MUTATION = """
mutation ProductCreate($input: ProductCreateInput!, $media: [CreateMediaInput!]) {
  productCreate(input: $input, media: $media) {
    product {
      id
      title
      description
      externalId
      weight
      weightUnit
      variants(first: 50) {
        edges {
          node {
            id
            sku
            options { name value }
            inventoryLevel { available }
          }
        }
      }
      media(first: 10) {
        edges {
          node { id url type }
        }
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

PRODUCT_UPDATE_MUTATION = """
mutation ProductUpdate($input: ProductUpdateInput!, $media: [CreateMediaInput!]) {
  productUpdate(input: $input, media: $media) {
    product {
      id
      title
      description
      externalId
      weight
      weightUnit
      variants(first: 50) {
        edges {
          node {
            id
            sku
            options { name value }
            inventoryLevel { available }
          }
        }
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

PRODUCT_DELETE_MUTATION = """
mutation ProductDelete($input: ProductDeleteInput!) {
  productDelete(input: $input) {
    deletedProductId
    userErrors {
      field
      message
      code
    }
  }
}
"""

# ── Product Variant Mutations ───────────────────────────────────────

PRODUCT_VARIANT_CREATE_MUTATION = """
mutation ProductVariantCreate($input: ProductVariantCreateInput!, $media: [CreateMediaInput!]) {
  productVariantCreate(input: $input, media: $media) {
    productVariant {
      id
      sku
      options { name value }
      inventoryLevel { available }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

PRODUCT_VARIANT_UPDATE_MUTATION = """
mutation ProductVariantUpdate($input: ProductVariantUpdateInput!, $media: [CreateMediaInput!]) {
  productVariantUpdate(input: $input, media: $media) {
    productVariant {
      id
      sku
      options { name value }
      inventoryLevel { available }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

PRODUCT_VARIANT_DELETE_MUTATION = """
mutation ProductVariantDelete($input: ProductVariantDeleteInput!) {
  productVariantDelete(input: $input) {
    deletedProductVariantId
    userErrors {
      field
      message
      code
    }
  }
}
"""

# ── Listing Mutations ───────────────────────────────────────────────

LISTING_UPDATE_MUTATION = """
mutation ListingUpdate($input: ListingUpdateInput!) {
  listingUpdate(input: $input) {
    listing {
      id
      status
      ... on BuyItNowListing {
        price { amount currencyCode }
        offerable
      }
      ... on AuctionListing {
        startingPrice { amount currencyCode }
        endTime
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

LISTING_DELETE_MUTATION = """
mutation ListingDelete($input: ListingDeleteInput!) {
  listingDelete(input: $input) {
    deletedListingId
    userErrors {
      field
      message
      code
    }
  }
}
"""

LISTING_PUBLISH_MUTATION = """
mutation ListingPublish($input: ListingPublishInput!) {
  listingPublish(input: $input) {
    listing {
      id
      status
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

LISTING_UNPUBLISH_MUTATION = """
mutation ListingUnpublish($input: ListingUnpublishInput!) {
  listingUnpublish(input: $input) {
    listing {
      id
      status
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

LISTING_ASSIGN_TO_LIVESTREAM_MUTATION = """
mutation ListingAssignToLivestream($input: ListingAssignToLivestreamInput!) {
  listingAssignToLivestream(input: $input) {
    listing {
      id
      status
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

LISTING_REMOVE_FROM_LIVESTREAM_MUTATION = """
mutation ListingRemoveFromLivestream($input: ListingRemoveFromLivestreamInput!) {
  listingRemoveFromLivestream(input: $input) {
    listing {
      id
      status
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

LISTING_ADJUST_QUANTITY_MUTATION = """
mutation ListingAdjustQuantity($input: ListingAdjustQuantityInput!) {
  listingAdjustQuantity(input: $input) {
    listing {
      id
      status
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

# ── Media & Upload Mutations ───────────────────────────────────────

MEDIA_DELETE_MUTATION = """
mutation MediaDelete($input: MediaDeleteInput!) {
  mediaDelete(input: $input) {
    deletedMediaId
    userErrors {
      field
      message
      code
    }
  }
}
"""

UPLOAD_CREATE_MUTATION = """
mutation UploadCreate($input: UploadCreateInput!) {
  uploadCreate(input: $input) {
    upload {
      url
      resourceUrl
      parameters {
        name
        value
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

# ── Bulk Operation Mutations ────────────────────────────────────────

BULK_OPERATION_RUN_QUERY_MUTATION = """
mutation BulkOperationRunQuery($input: BulkOperationRunQueryInput!) {
  bulkOperationRunQuery(input: $input) {
    bulkOperation {
      id
      status
      type
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

BULK_OPERATION_RUN_MUTATION_MUTATION = """
mutation BulkOperationRunMutation($input: BulkOperationRunMutationInput!) {
  bulkOperationRunMutation(input: $input) {
    bulkOperation {
      id
      status
      type
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

BULK_OPERATION_CANCEL_MUTATION = """
mutation BulkOperationCancel($input: BulkOperationCancelInput!) {
  bulkOperationCancel(input: $input) {
    bulkOperation {
      id
      status
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

# ── Order Mutations ─────────────────────────────────────────────────

ADD_TRACKING_CODE_MUTATION = """
mutation AddTrackingCode($input: AddTrackingCodeInput!) {
  addTrackingCode(input: $input) {
    order {
      id
      status
      trackingInfo {
        trackingCompany
        trackingNumber
        trackingUrl
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

ORDER_CANCEL_MUTATION = """
mutation OrderCancel($input: OrderCancelInput!) {
  orderCancel(input: $input) {
    order {
      id
      status
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""
