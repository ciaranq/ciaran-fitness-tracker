# Recovery Session Runner: Design

Status: **APPROVED by user 2026-11-04.** Node: **G12**.
Owners: AGY builds `frontend/` and the watcher extension; Claude owns the DB schema (`backend/engine/db.py`) and planner interaction.

## 1. Intent

Ciaran is in the gym with only a phone and no wifi. He wants to open a routine, tap Start, and be walked through it hands-free: the app announces the start, then each exercise in turn, until the routine is done. He can pause at any time. After the session, his data reaches the tracker later, without signal being needed in the gym.

This is part of the **Recovery** section of the app. The first two routines come from the physio recovery plan assessed 02 Nov 2026 (the Move Health schedule): **`physio_strength`** (11 strength exercises, 3 x 10) and **`physio_stretches`** (5 daily stretches, timed holds). They are separate routines the user starts independently. More routines will be added later, so routines must be data, not hard-coded screens.

Why it matters: the planner's progression and flare logic (`session_log`) only works if real sessions are logged. Today there is no way to log one from the gym.

## 2. Goals

- Run a routine start to finish on a phone with **no network** after the first install.
- Spoken announcements (start, each exercise, set number, rest, finish) plus the same information on screen. Pause, resume, and skip.
- Routines come from data. The two physio routines are derived from `frontend/src/data/rehab-plan.json` by exercise `group` (strength vs `stretch_` ids): 11 strength items at 3 x 10, and 5 stretches with a 30 s hold. A further routine must be addable by adding data only.
- Log each set locally on the phone. Export a session to a file, drop it into `data/raw/ingest/` on the Mac, and the existing watcher ingests it.
- Re-dropping the same file must never create duplicate rows (idempotent).

## 3. Non-goals (first version)

- Automatic background sync to a deployed backend. That is a later upgrade and needs hosting, auth and CORS fixed first (HANDOFF.md section 4, finding 2).
- Editing routines in the app, weight tracking, notes, charts, video demos.
- Multi-user or accounts.
- Changing planner rules or `physio_plans` content.

## 4. Anti-goals

- Anything that requires signal mid-session. A session that fails because the page tried to fetch something is a failure even if it works at home.
- Losing a logged set. If the phone is locked, the tab is backgrounded, or the app is closed mid-session, completed sets must survive.
- Duplicate or corrupted rows after dropping a file twice, or a half-copied file.
- Surfacing personal health data on a public URL. The site is behind Vercel Authentication (`all`); do not weaken that to make offline easier without asking.

## 5. Decisions made by the user

| Decision | Choice |
|---|---|
| Where data goes after the gym | **Export a file, drop it in the hot folder** (not auto-sync). Auto-sync is a later upgrade. |
| What a routine run looks like | Spoken walkthrough, in order, pausable, offline |
| Where it lives | Recovery section of the app |
| Routines | Several, data-driven. The physio plan is **two separate routines**: strength (11) and stretches (5) |
| Process | Iterate after real use |

## 6. Calls made by Claude (not agreed; user to confirm or change)

- **Per-set log fields:** `set_id`, `session_id`, `routine_id`, `exercise_id`, `set_number`, `reps_done` (pre-filled with the prescribed reps), `performed_at`, optional `symptom` using the planner's existing values: `posterior_right_knee`, `left_sciatic_radiation`, `shoulder_pain`. Weight and notes are deferred.
- **Rest timer** between sets with a default length (suggest 60 s; the physio gave no number, so mark it an assumption in the UI, as the plan JSON already does for assumed values). Configurable per routine data.
- **Stretches** run as timed holds per side using `hold_seconds`; strength runs as rep counts the user confirms.
- **Symptom during a set** stops the routine and shows the planner's stop rule text. It does not decide clinical state; the flare decision stays in the planner on ingest.
- **Spoken cues (user raised 2026-11-04):** each exercise may carry a short `cue_text` (how to do it, what to watch for), spoken by speech synthesis. Source order: (1) the physio's own wording already in `rehab-plan.json` `notes`, (2) text the user supplies, (3) generic descriptions found online, only to fill gaps and clearly marked as generic, not the physio's. The user offered to record the Move Health voice clips himself; support an optional per-exercise `cue_audio` file that overrides speech synthesis when present and is cached for offline use. I will not scrape or copy Move Health's content. Audio files are bundled with the app, so they go in the cached shell and must not contain anything personal.
- **IDs:** `session_id` and `set_id` are client-generated UUIDs. They are the idempotency keys.

## 7. Behaviour

1. **Pick:** Recovery page lists routines (Strength, Stretches, and any added later). Tap one, see its exercise list, tap Start.
2. **Run:** announce "Starting <routine>", then per exercise: name, then "set N of M", reps or hold. Strength: user taps Done after the set (reps pre-filled, adjustable). Stretch: timer counts the hold and announces completion. Rest timer between sets. Next exercise announced automatically.
3. **Pause / resume / skip / end early.** Skipped and unfinished exercises are recorded as such, not logged as done.
4. **Symptom:** one-tap tag on any set; triggers the stop-and-review screen.
5. **Finish:** summary, then **Export** produces one JSON file for the session. The session stays on the phone until the user marks it exported; exporting again is safe.

## 8. Offline architecture

- **Installable PWA** (home-screen app) with a service worker that caches the app shell, the routine data and fonts. First load must happen with signal.
- **Local store:** IndexedDB for sessions and sets, written after every set (not at the end).
- **Speech:** the Web Speech API `speechSynthesis` with on-device voices; started from the Start tap (a user gesture is required on iOS).
- **Screen Wake Lock** so the screen stays on and speech continues.
- **Export:** Web Share API with a file where supported, otherwise a download link. File name `session-<session_id>.json`.
- The runner must not call any `/api/*` route.

## 9. Ingest and data model

Export file shape (one session):

```json
{
  "type": "workout_session",
  "version": 1,
  "session_id": "<uuid>",
  "routine_id": "physio_strength",
  "started_at": "<ISO-8601>",
  "ended_at": "<ISO-8601>",
  "sets": [
    {"set_id": "<uuid>", "exercise_id": "squat_green_band", "set_number": 1,
     "reps_done": 10, "performed_at": "<ISO-8601>", "symptom": null}
  ]
}
```

- **Contract:** add a Pydantic model for it in `backend/ingestion/contracts.py` (AGY).
- **Watcher:** `_parse_record_dict` currently raises "Unrecognized biometric record schema" for anything that is not vitals or activity. Add a `workout_session` branch that writes to `app_state.db` (AGY, `backend/ingestion/watcher.py`).
- **Schema (Claude, `backend/engine/db.py`):** new SQLite table `set_log` with `set_id TEXT PRIMARY KEY`, plus `session_id`, `routine_id`, `exercise_id`, `set_number`, `reps_done`, `performed_at`, `symptom`. Insert with `OR IGNORE` on `set_id` so re-drops are no-ops.
- **Planner compatibility:** `session_log` has no unique key and no session id, and the progression logic counts consecutive clean sessions per exercise from it. On ingest, add **one `session_log` row per exercise per session** (symptom set if any set of that exercise had one), and only when that exercise's sets were newly inserted. Exact approach is left to the builder, but a re-drop must not add `session_log` rows.
- `session_log.symptom` values must be exactly the planner's `Symptom` values.

## 10. Dependencies and risks

| # | Item | Notes |
|---|---|---|
| 1 | **Watcher reads half-written files.** AirDrop and copy write incrementally; `on_created` fires first (audit finding 4). | **Must be fixed before this ships**: settle delay or retry, and a quarantine folder for bad files. |
| 2 | **Service worker vs Vercel Authentication.** Fetches for the page and service worker may be redirected to Vercel login, which could break install or offline caching. | Verify in a first spike on a real phone. If it fails, the user decides how to expose the page (I will not change protection unasked). |
| 3 | **Wake lock and speech with a locked screen** on iOS standalone PWAs. I am not certain these behave reliably. | Test on the user's phone early. Fallback: on-screen prompts plus a short audio cue. |
| 4 | **Browser storage eviction.** I am not certain how long iOS keeps IndexedDB for a site that is not installed. | Installing to the home screen is expected; show an "unexported sessions" warning. |
| 5 | **Share-sheet support for JSON files** varies by browser. | Provide the download fallback. |
| 6 | **New dependencies** (a PWA/service-worker helper, if any) need user approval before install. | Prefer a hand-written service worker. |
| 7 | **Flare-resolution rule lives in the router, not the planner** (audit finding 5). Session ingest feeds it. | Not changed here; tracked separately. |

## 11. Left to the builder

- Component structure, routing (`/recovery`, `/recovery/[routine]`), and styling within the existing glassmorphic system.
- Service worker approach and cache strategy.
- Voice selection, announcement wording, rest-timer UX, and the `cue_text` / `cue_audio` data shape.
- How routine data is shaped beyond what the physio JSON already provides (must support more than one routine).
- Test plan. At minimum: contract tests, watcher tests including duplicate drops and partial files, and an offline run verified on a real phone.

## 12. Acceptance

- Airplane-mode run of both physio routines on the user's phone (`physio_strength`: 11 exercises; `physio_stretches`: 5 timed holds), including pause, resume and a symptom stop.
- Export, drop into `data/raw/ingest/`, rows appear in `set_log` and `session_log`; dropping the same file again adds no rows.
- `uv run --directory backend pytest` and `bun run --cwd frontend build` pass.
