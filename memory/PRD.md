# AgriRent Pro — Product Requirements

## Original problem statement
> a tool renting system where farmer can rent any kind  of tool relatead to farming

## Product context
AgriRent Pro is a demo-ready farming equipment rental marketplace for farmers, tool owners, and administrators. The selected MVP is intentionally sign-in-free so users can explore the experience quickly.

## User personas
- **Farmer:** searches local farming tools, compares hourly/daily rates, sends rental requests, and reviews history.
- **Tool owner:** understands the marketplace context and can be represented through the role switcher while the owner management backlog is developed.
- **Admin:** can preview the admin workspace persona and will later manage catalog and requests.

## Architecture decisions
- React frontend with responsive CSS and Lucide icons.
- FastAPI backend with MongoDB using the protected `MONGO_URL` and `DB_NAME` environment values.
- REST endpoints under `/api` for tools and rentals.
- Seed-on-first-read tool catalog so the demo has useful content without manual setup.
- No authentication, payments, or external integrations in this MVP.

## Core requirements (static)
- Browse and search farming tools.
- Filter by category and availability.
- Show tool image, owner, location, rating, and hourly/daily pricing.
- Open a rental request modal with unit selection, duration stepper, and total preview.
- Persist rental requests and show rental history.
- Provide Farmer, Tool Owner, and Admin demo role switching.
- Maintain usable desktop and mobile layouts.

## What's been implemented

### 2026-09-20
- Replaced starter splash screen with AgriRent Pro dashboard.
- Added seeded tractors, harvester, tiller, and seed drill catalog records.
- Added `/api/tools`, `/api/tools/{tool_id}`, `/api/rentals` GET and POST endpoints.
- Added search, category filters, availability toggle, responsive mobile navigation, role switcher, rental modal, pricing calculator, request confirmation, and rental history.
- Verified backend API, production frontend build, and browser flow at desktop/mobile sizes with 100% test success.

## Prioritized backlog

### P0 — next core release
- Tool owner catalog management: create, edit, pause, and remove listings.
- Admin request queue with approve/reject status changes.
- Date-range availability calendar and conflict prevention.

### P1 — trust and operations
- Farmer and owner accounts with secure authentication.
- Rental pickup/return details and contact information.
- Notifications for request status changes.

### P2 — growth
- Online payments and invoices.
- Ratings and reviews after completed rentals.
- Location radius search and map-based discovery.

## Next tasks
1. Build owner listing management with availability controls.
2. Add admin approval workflow for incoming rental requests.
3. Add date-based booking availability.
4. Add post-rental ratings and reviews.