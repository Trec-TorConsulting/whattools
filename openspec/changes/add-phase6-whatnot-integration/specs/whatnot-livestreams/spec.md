## ADDED Requirements

### Requirement: Livestream Sync
The system SHALL import livestream data from Whatnot including title, creation date, and order count. Livestreams SHALL be mapped to the existing WhatTools "shows" model.

#### Scenario: Pull livestreams from Whatnot
- **WHEN** livestream sync is triggered
- **THEN** the system queries Whatnot's `livestreams` endpoint
- **AND** creates or updates local show records with `whatnot_livestream_id`

#### Scenario: Link orders to livestreams
- **WHEN** an order has a LIVESTREAM sales channel with a reference ID
- **THEN** the system links the order to the corresponding local show via `whatnot_livestream_id`
