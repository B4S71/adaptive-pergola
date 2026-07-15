# Config-flow condensation (feature/visual-config-flow)

Goal: strip the Adaptive-Cover-Pro heritage out of the configuration flow so a
pergola is configured with only the parameters a pergola needs. Agreed scope
(2026-07-15):

**Cut** — building profiles (whole subsystem), duplicate & selective sync,
glare zones, blind-spot UI (engine support stays), interpolation,
quick/full setup fork.

**Keep** — geometry, positions/schedule/morning, weather safety, manual
override, cloud suppression, climate, automation/deltas/re-sync,
motion/presence override, pipeline-priorities editor, all 10 custom-position
slots (slot 1 = live frost template).

**Reframe** — window azimuth + FOV left/right → a "sun window":
`sun window start azimuth` / `sun window end azimuth` (clockwise range the
shading reacts to), optional min/max elevation unchanged.

## Stages

1. **Flow condensation (this stage)** — creation flow goes straight to the
   cover form (no create-menu, no building-profile creation, no duplicate
   entry point, no quick/full fork — the previous "quick" path IS the flow).
   Options menu drops `building_profile`, `blind_spot`, `interp`,
   `glare_zones`, `sync`. All backend code stays dormant; step handlers remain
   callable (tests that drive steps directly keep passing).

2. **Sun-window reframe** — replace `set_azimuth`/`fov_left`/`fov_right`
   presentation in the sun-tracking step with two transient fields
   `sun_window_start` / `sun_window_end` (0–359°, clockwise start→end,
   wrap-aware). Canonical storage stays `set_azimuth` (window midpoint) +
   symmetric `fov_left == fov_right == span/2`, so the engine, live entries
   and diagnostics are untouched. Derivation on form load:
   `start = (azimuth − fov_left) % 360`, `end = (azimuth + fov_right) % 360`.
   Save: `span = (end − start) % 360`, `mid = (start + span/2) % 360`.
   Transient-field pattern: pop before persist, like `CONF_FOV_COMPUTE`.
   Translations en/de/fr for both flow copies of the step.

3. **Per-step key pruning** — drop heritage keys from the remaining step
   schemas where they are meaningless for a tilt-only pergola
   (`inverse_state`, `open_close_threshold`?, `enable_my_position_entities`?,
   `transparent_blind`, `distance_shaded_area`, vertical-cover geometry
   remnants). Each key removed needs: schema, sync-coverage exemptions,
   options-service section, translations, tests.

4. **Dead-code deletion** — remove `profile_link.py`, `building_overview.py`,
   profile/duplicate/sync step handlers, `SYNC_CATEGORIES` machinery and the
   sync-coverage test scaffolding, glare-zone/interp/blind-spot flow code +
   translations. Rewrite `tests/test_sync_coverage.py` guard into a plain
   "every schema key is known" check. Bump 0.6.0-beta1.

Sequencing note: stages are individually shippable; stage 4 is the big test
churn (hundreds of profile/sync/duplicate tests get deleted with the code).
