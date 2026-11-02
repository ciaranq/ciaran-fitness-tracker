# REQUIREMENTS.md: Ciaran Fitness Tracker

## 1. Overview
Cardio-pulmonary health and fitness engine aggregating Garmin Connect, Polar HR strap, QardioArm BP, Apple Health steps, and Spirometer Peak Flow data with adaptive physio scheduling.

## 2. Storage Architecture
- Analytical: `biometrics.duckdb` for high-density time-series.
- Operational: `app_state.db` (SQLite) for physio protocols and Google sync states.
- Hot-Folder Ingest: `data/raw/ingest/` monitored by `backend/ingestion/watcher.py`.
