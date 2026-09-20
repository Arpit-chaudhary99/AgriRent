# AgriRent Pro — PRD

## Overview
Tool rental system for farmers with role-based access (USER, ADMIN). Farmers browse farming equipment, pick rental dates, pay via Razorpay UPI/Cards. Admins manage inventory, users, rentals and payments.

## Stack
- Backend: FastAPI + MongoDB + Razorpay + Emergent Object Storage
- Frontend: React (CRA) + React Router + Sonner (toasts)
- Auth: Emergent-managed Google Sign-in
- Payments: Razorpay Test Mode

## Roles
- **USER**: browse tools, request rentals with start/end dates, cancel Requested rentals, pay approved rentals, view own payment history, manage profile
- **ADMIN** (assigned by `ADMIN_EMAIL` env var): everything USER can do + admin console with tools/users/rentals/payments management

## Implemented
- Google sign-in (Emergent), session cookie + Authorization header fallback, `/api/auth/me`, blocked-user gating (2026-02-20)
- Rental with start_date / end_date (2026-02-20)
- User isolation on `/api/rentals`, `/api/payments/history` (2026-02-20)
- Admin panel: dashboard stats, tools CRUD + image upload (Emergent Object Storage), users list + block/unblock, rentals list + approve, payments ledger (2026-02-20)
- Razorpay UPI checkout with retry + failure handlers, webhook, server-side signature verification (previous iterations)

## Backlog
- P1: Real email receipt via Resend after successful payment
- P1: Refunds from admin ledger
- P2: Multi-image gallery per tool
- P2: Booking calendar with conflict detection (right now dates don't block overlapping rentals)
- P3: Analytics — weekly revenue chart

## Migration Notes
- One-time: on startup, legacy rentals (created before auth) are wiped (`user_id` missing → delete). Same for orphan payments.
- New user field: `role` (USER | ADMIN), `blocked` (bool)
- New Rental fields: `user_id`, `user_email`, `start_date`, `end_date`, `days` (replaces `duration` + `unit`)
