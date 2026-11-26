# Agent instructions

## Home Assistant dashboards

- Dashboard layouts and Lovelace cards are UI-managed in the live Home Assistant instance; they are not stored in this repository. Start at **Settings → Dashboards**, select the dashboard, and inspect its views before editing. Do not assume `packages/dashboard.yaml` contains dashboard cards; it only defines shared template sensors.
- Read [the dashboard map](docs/dashboards.md) for known dashboard names, URLs, and their repository-backed entities.
- The kitchen weather screensaver includes custom JavaScript inside a `custom:mod-card`. Keep the visible chips, tap behavior, and popup filters consistent when changing parcel or post-office behavior.
- Keep entity logic and automations in YAML packages. The screensaver's visual card configuration remains in the Home Assistant dashboard editor.
