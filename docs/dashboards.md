# Home Assistant dashboard map

Home Assistant stores these dashboards as UI-managed configuration. Their card YAML is not present in this repository, so make visual changes through **Settings → Dashboards** in the live instance. Use the dashboard list and each view's URL to confirm the target before editing.

## Kitchen tablet

| Dashboard / view | URL | What it contains | Where to change it |
| --- | --- | --- | --- |
| Kitchen Tablet / Controls | `/kitchen-tablet/ambient` | Kitchen tablet controls and room/device sections | Edit the **Kitchen Tablet** dashboard in Home Assistant. |
| מזג האוויר / Ambient | `/kitchen-weather/ambient` | Kitchen screensaver weather, post-office chip, and parcel chips with detail popups | Edit the **מזג האוויר** dashboard's `ambient` view. Its main card is a `custom:mod-card` containing `custom:button-card` JavaScript and styles. |

The screensaver's chip counts, popup matching, and parcel details live together in that custom card. Keep the in-transit list/count excluding packages classified as pickup ready (`נשלח מסרון הגעה ליחידה`), and keep pickup-ready packages in the pickup popup with their tracking number, pickup code, status, update text, and date. Match pickup codes from `input_text.kitchen_tablet_pickup_codes` by tracking number; do not hardcode codes in the dashboard.

The [Kiosk Satellite setup](kiosk-satellite/README.md#weather-screensaver-and-parcel-tables) owns the idle view and background tap. Keep the card's `data-kitchen-parcel-open`, `data-kitchen-post-office-open`, and `.parcel-popup-content` selectors in sync with the kiosk script so that chips and table controls receive taps. Attach the **סגירה** action to the close button's `click` when creating the popup. The card's `pointerdown` handler leaves the popup visible on that button so the completed tap still lands inside the table and stays on the weather view.

The iOS Messages automation should POST its SMS text as JSON `{ "message": "..." }` to the Home Assistant webhook configured by `kitchen_tablet_receive_israel_post_pickup_sms` in the kitchen tablet package. Home Assistant extracts the tracking number and the Hebrew pickup letter plus four-digit code, and stores only those parsed values for the dashboard. The iPhone Shortcut configuration is device-local and is not in this repository.

## YAML-backed entities

Dashboard cards are UI-managed, but their data sources belong in packages:

- [Kitchen tablet package](../packages/kitchen_tablet/kitchen_tablet.yaml): tablet automations and template sensors, including active parcel details and pickup/transit counts.
- [Post office package](../packages/post_office.yaml): post-office opening state and next opening/closing sensors used by the screensaver chip and schedule popup.
- [Dashboard package](../packages/dashboard.yaml): shared time-of-day template sensor only; it does not define dashboard layouts.

When a card references a new entity, add its template/helper to the owning YAML package and keep the live dashboard reference in sync. Check **Settings → Dashboards** for other dashboards and views; do not infer dashboard locations from package filenames.
