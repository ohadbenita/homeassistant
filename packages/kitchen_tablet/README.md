# Kitchen tablet

Keep tablet-specific Home Assistant automations, template sensors, and
dashboard changes in this directory. [kitchen_tablet.yaml](./kitchen_tablet.yaml)
loads the package and registers the [managed dashboard](./dashboard.yml).
The dashboard file uses `.yml` so Home Assistant's package directory scan
does not load it as a separate package.

The parcel details view reads the two active statuses from 17TRACK. The
freezer warning appears after the pantry freezer door has been open for
five minutes and clears when the door closes.

## Switch to the managed dashboard

After Home Assistant loads the package on restart, check that both managed
views render. Set these Kiosk Satellite URLs on the tablet:

| Setting | Path |
| --- | --- |
| Start URL | `/kitchen-tablet-managed/controls` |
| Website screensaver URL | `/kitchen-tablet-managed/ambient` |

The controls view has a parcel shortcut. To open details directly from a
badge on the Website screensaver, enable **Double tap to dismiss** in Kiosk
Satellite. This changes the gesture for returning to the controls.

## Kiosk settings backup

The [settings snapshot](./kitchen-fire-tablet.settings.json) comes from the
Kitchen Fire Tablet export. It includes reverse portrait orientation, adaptive
brightness from the kitchen FP2, the one-minute idle timer, and dashboard
styling and tap feedback.

### Restore

For a full restore, use **Device → Configuration → Import configuration** in
Kiosk Satellite Remote Admin with the original export from private storage.

The JSON in this directory is a partial snapshot. It excludes credentials,
server addresses, and browser local storage. Use it as a settings reference or
send it as the body of an authenticated `PATCH /api/settings` request to Kiosk
Satellite. Supply the Home Assistant connection details and managed dashboard
paths separately.

Grant the required tablet permissions and set the RTSP credentials on the
tablet.

See the [Kiosk Satellite remote API documentation][remote-api] for details.

[remote-api]: https://kiosksatellite.com/docs/remote-api/

## Screensaver schedule

The tablet uses Black from 00:00 to 06:00 and the Home Assistant weather
dashboard from 06:00 to midnight. Face wake is off. Manage the schedule under
**Screensaver → Schedule** in Kiosk Satellite Remote Admin.
