# Kitchen tablet kiosk backup

The [settings snapshot](./kitchen-fire-tablet.settings.json) comes from the
Kitchen Fire Tablet export. It includes Weather Mood, the five-minute idle
timer, front-camera wake, and the dashboard styling and tap feedback.

## Restore

For a full restore, use **Device → Configuration → Import configuration** in
Kiosk Satellite Remote Admin with the original export from private storage.

The JSON in this directory is a partial snapshot. It excludes credentials,
server addresses, and browser local storage. Use it as a settings reference or
send it as the body of an authenticated `PATCH /api/settings` request to Kiosk
Satellite. Supply the Home Assistant connection details separately, select
the Kitchen Tablet dashboard, and grant the required permissions on the tablet.
Restore the dashboard itself from a Home Assistant backup.

See the [Kiosk Satellite remote API documentation][remote-api] for details.

[remote-api]: https://kiosksatellite.com/docs/remote-api/

## Sunset screensaver schedule

The kitchen kiosk package uses Home Assistant's home location and time zone
to send the local sunset time to the tablet. The tablet keeps the schedule
locally and starts Celestial at sunset, Black at midnight, and Weather Mood
at 06:00. The Black entry disables face and motion wake and leaves tap to wake
available. Keep the kiosk's physical screen-off timer at zero for tap to wake.

Before deploying the package, set `kitchen_kiosk_settings_url` to the tablet's
`/api/settings` endpoint and `kitchen_kiosk_api_authorization` to its full
`Bearer` authorization header in Home Assistant's private `secrets.yaml`.
After the Git sync, reload RESTful Command and run **Kitchen kiosk - Schedule
Celestial at sunset** once to send the schedule immediately. Keep the tablet's
time zone in sync with Home Assistant and use its home location for Celestial.
