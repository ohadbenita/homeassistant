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

## Screensaver schedule

Manage the active schedule under **Screensaver → Schedule** in Kiosk Satellite
Remote Admin.
