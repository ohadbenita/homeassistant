# Kitchen tablet kiosk backup

The [settings snapshot](./kitchen-fire-tablet.settings.json) comes from the
Kitchen Fire Tablet export. It includes reverse portrait orientation, adaptive
brightness from the kitchen FP2, the one-minute idle timer, and dashboard
styling and tap feedback.

## Restore

For a full restore, use **Device → Configuration → Import configuration** in
Kiosk Satellite Remote Admin with the original export from private storage.

The JSON in this directory is a partial snapshot. It excludes credentials,
server addresses, and browser local storage. Use it as a settings reference or
send it as the body of an authenticated `PATCH /api/settings` request to Kiosk
Satellite. Supply the Home Assistant connection details separately. Use your
Home Assistant server address with the following paths.

| Setting | Path |
| --- | --- |
| Start URL | `/kitchen-tablet/ambient` |
| Website screensaver URL | `/kitchen-weather/ambient` |

Grant the required tablet permissions and set the RTSP credentials on the
tablet. Restore the dashboard itself from a Home Assistant backup.

See the [Kiosk Satellite remote API documentation][remote-api] for details.

[remote-api]: https://kiosksatellite.com/docs/remote-api/

## Screensaver schedule

The tablet uses Black from 00:00 to 06:00 and the Home Assistant weather
dashboard from 06:00 to midnight. Face wake is off. Manage the schedule under
**Screensaver → Schedule** in Kiosk Satellite Remote Admin.
