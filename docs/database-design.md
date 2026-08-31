# NammaNexus AI — Database Design

## Database

PostgreSQL with PostGIS.

## Purpose

The database stores structured civic information, complaint records, locations, authority relationships, AI results, and application state.

## Initial SpotFix Entity

The first major entity is Complaint.

## Complaint Data

A complaint may contain:

- Complaint ID
- Status
- Issue category
- User description
- Latitude
- Longitude
- Image storage key
- AI severity
- AI confidence
- AI visual description
- Ward reference
- Authority reference
- Complaint subject
- Complaint body
- Created timestamp
- Updated timestamp

## Image Storage

Images are not stored directly inside PostgreSQL.

The database stores an image storage reference.

The original image is stored using the application's StorageService.

## Geospatial Data

PostGIS will be used for:

- Location queries
- Ward boundary matching
- Jurisdiction resolution
- Future spatial queries

## Database Access

FastAPI
↓
SQLAlchemy
↓
PostgreSQL/PostGIS

## Database Migrations

Alembic will manage schema changes through versioned migrations.

## Design Principle

The database will be expanded incrementally as new SpotFix requirements are implemented.

Tables and relationships should not be created without a concrete requirement.