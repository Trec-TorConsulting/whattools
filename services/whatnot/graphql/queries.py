"""GraphQL read queries for the Whatnot Seller API."""

# ── Product Queries ─────────────────────────────────────────────────

PRODUCTS_QUERY = """
query Products($first: Int, $after: String, $before: String, $last: Int, $reverse: Boolean, $sortKey: ProductSortKey) {
  products(first: $first, after: $after, before: $before, last: $last, reverse: $reverse, sortKey: $sortKey) {
    edges {
      cursor
      node {
        id
        title
        description
        externalId
        weight
        weightUnit
        hazardousMaterial
        productTaxonomyNode {
          id
          name
          fullName
        }
        shippingProfile {
          id
        }
        variants(first: 50) {
          edges {
            node {
              id
              sku
              options {
                name
                value
              }
              inventoryLevel {
                available
              }
              media(first: 10) {
                edges {
                  node {
                    id
                    url
                    type
                    mimeType
                    alt
                    sortOrder
                  }
                }
              }
              listings(first: 10) {
                edges {
                  node {
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
                }
              }
            }
          }
        }
        media(first: 10) {
          edges {
            node {
              id
              url
              type
              mimeType
              alt
              sortOrder
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
  }
}
"""

PRODUCT_QUERY = """
query Product($id: ID!) {
  product(id: $id) {
    id
    title
    description
    externalId
    weight
    weightUnit
    hazardousMaterial
    productTaxonomyNode {
      id
      name
      fullName
    }
    shippingProfile {
      id
    }
    variants(first: 50) {
      edges {
        node {
          id
          sku
          options {
            name
            value
          }
          inventoryLevel {
            available
          }
          media(first: 10) {
            edges {
              node {
                id
                url
                type
                mimeType
                alt
                sortOrder
              }
            }
          }
          listings(first: 10) {
            edges {
              node {
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
            }
          }
        }
      }
    }
    media(first: 10) {
      edges {
        node {
          id
          url
          type
          mimeType
          alt
          sortOrder
        }
      }
    }
  }
}
"""

# ── Product Variant Queries ─────────────────────────────────────────

PRODUCT_VARIANTS_QUERY = """
query ProductVariants($first: Int, $after: String, $filter: ProductVariantFilter) {
  productVariants(first: $first, after: $after, filter: $filter) {
    edges {
      cursor
      node {
        id
        sku
        options {
          name
          value
        }
        product {
          id
          title
        }
        inventoryLevel {
          available
        }
        media(first: 10) {
          edges {
            node {
              id
              url
              type
              mimeType
              alt
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

PRODUCT_VARIANT_QUERY = """
query ProductVariant($id: ID!) {
  productVariant(id: $id) {
    id
    sku
    options {
      name
      value
    }
    product {
      id
      title
    }
    inventoryLevel {
      available
    }
    media(first: 10) {
      edges {
        node {
          id
          url
          type
          mimeType
          alt
        }
      }
    }
    listings(first: 10) {
      edges {
        node {
          id
          status
          ... on BuyItNowListing {
            price { amount currencyCode }
          }
          ... on AuctionListing {
            startingPrice { amount currencyCode }
          }
        }
      }
    }
  }
}
"""

# ── Listing Queries ─────────────────────────────────────────────────

LISTINGS_QUERY = """
query Listings($first: Int, $after: String, $filter: ListingFilter, $sortKey: ListingSortKey) {
  listings(first: $first, after: $after, filter: $filter, sortKey: $sortKey) {
    edges {
      cursor
      node {
        id
        status
        ... on BuyItNowListing {
          price { amount currencyCode }
          offerable
        }
        ... on AuctionListing {
          startingPrice { amount currencyCode }
          endTime
          suddenDeath
        }
        ... on GiveawayListing {
          __typename
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

LISTING_QUERY = """
query Listing($id: ID!) {
  listing(id: $id) {
    id
    status
    ... on BuyItNowListing {
      price { amount currencyCode }
      offerable
    }
    ... on AuctionListing {
      startingPrice { amount currencyCode }
      endTime
      suddenDeath
    }
    ... on GiveawayListing {
      __typename
    }
  }
}
"""

# ── Order Queries ───────────────────────────────────────────────────

ORDERS_QUERY = """
query Orders($first: Int, $after: String, $filter: OrderFilter, $sortKey: OrderSortKey) {
  orders(first: $first, after: $after, filter: $filter, sortKey: $sortKey) {
    edges {
      cursor
      node {
        id
        status
        isGiveaway
        subtotal { amount currencyCode }
        shippingPrice { amount currencyCode }
        taxation { amount currencyCode }
        total { amount currencyCode }
        salesChannel {
          type
          reference
        }
        trackingInfo {
          trackingCompany
          trackingNumber
          trackingUrl
        }
        customer {
          id
          username
          displayName
          email
        }
        shippingAddress {
          id
          fullName
          line1
          line2
          city
          state
          postalCode
          phoneNumber
          countryCode
        }
        items(first: 50) {
          edges {
            node {
              id
              quantity
              isPickup
              price { amount currencyCode }
              subtotal { amount currencyCode }
              product {
                id
                title
                externalId
              }
              variant {
                id
                sku
              }
              listing {
                id
              }
            }
          }
        }
        createdAt
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

ORDER_QUERY = """
query Order($id: ID!) {
  order(id: $id) {
    id
    status
    isGiveaway
    subtotal { amount currencyCode }
    shippingPrice { amount currencyCode }
    taxation { amount currencyCode }
    total { amount currencyCode }
    salesChannel {
      type
      reference
    }
    trackingInfo {
      trackingCompany
      trackingNumber
      trackingUrl
    }
    customer {
      id
      username
      displayName
      email
    }
    shippingAddress {
      id
      fullName
      line1
      line2
      city
      state
      postalCode
      phoneNumber
      countryCode
    }
    items(first: 50) {
      edges {
        node {
          id
          quantity
          isPickup
          price { amount currencyCode }
          subtotal { amount currencyCode }
          product {
            id
            title
            externalId
          }
          variant {
            id
            sku
          }
          listing {
            id
          }
        }
      }
    }
    createdAt
  }
}
"""

# ── Livestream Queries ──────────────────────────────────────────────

LIVESTREAMS_QUERY = """
query Livestreams($first: Int, $after: String, $sortKey: LivestreamSortKey) {
  livestreams(first: $first, after: $after, sortKey: $sortKey) {
    edges {
      cursor
      node {
        id
        title
        createdAt
        numOrders
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

LIVESTREAM_QUERY = """
query Livestream($id: ID!) {
  livestream(id: $id) {
    id
    title
    createdAt
    numOrders
  }
}
"""

# ── Taxonomy Queries ────────────────────────────────────────────────

TAXONOMY_NODES_QUERY = """
query TaxonomyNodes($first: Int, $after: String, $filter: ProductTaxonomyNodeFilter, $sortKey: ProductTaxonomyNodeSortKey) {
  productTaxonomyNodes(first: $first, after: $after, filter: $filter, sortKey: $sortKey) {
    edges {
      cursor
      node {
        id
        name
        fullName
        isLeaf
        parentId
        childrenIds
        level
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

TAXONOMY_NODE_QUERY = """
query TaxonomyNode($id: ID!) {
  productTaxonomyNode(id: $id) {
    id
    name
    fullName
    isLeaf
    parentId
    childrenIds
    level
  }
}
"""

# ── Product Attribute Queries ───────────────────────────────────────

PRODUCT_ATTRIBUTES_QUERY = """
query ProductAttributes($first: Int, $after: String, $filter: ProductAttributeFilter) {
  productAttributes(first: $first, after: $after, filter: $filter) {
    edges {
      cursor
      node {
        id
        name
        handle
        description
        values
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

PRODUCT_ATTRIBUTE_QUERY = """
query ProductAttribute($id: ID!) {
  productAttribute(id: $id) {
    id
    name
    handle
    description
    values
  }
}
"""

# ── Bulk Operation Queries ──────────────────────────────────────────

BULK_OPERATIONS_QUERY = """
query BulkOperations($first: Int, $after: String, $filter: BulkOperationFilter, $sortKey: BulkOperationSortKey) {
  bulkOperations(first: $first, after: $after, filter: $filter, sortKey: $sortKey) {
    edges {
      cursor
      node {
        id
        status
        type
        createdAt
        completedAt
        url
        errorCode
        objectCount
        rootObjectCount
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

BULK_OPERATION_QUERY = """
query BulkOperation($id: ID!) {
  bulkOperation(id: $id) {
    id
    status
    type
    createdAt
    completedAt
    url
    errorCode
    objectCount
    rootObjectCount
  }
}
"""

CURRENT_BULK_OPERATION_QUERY = """
query CurrentBulkOperation($type: BulkOperationType!) {
  currentBulkOperation(type: $type) {
    id
    status
    type
    createdAt
    completedAt
    url
    errorCode
    objectCount
    rootObjectCount
  }
}
"""

# ── User Query ──────────────────────────────────────────────────────

ME_QUERY = """
query Me {
  me {
    id
    username
    displayName
    currencyCode
    countryCode
    image {
      url
    }
    features
  }
}
"""
