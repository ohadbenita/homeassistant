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

| Setting | Value |
| --- | --- |
| Start URL | `/kitchen-tablet/ambient` |
| Idle timeout | 60 seconds |
| Screensaver mode | Dim |
| Dim level | 100% ceiling with adaptive brightness |
| Double tap to dismiss | Off in both Dashboard and Website modes |
| Scheduled screensavers | Off |

Grant the required tablet permissions and set the RTSP credentials on the
tablet. Restore the dashboard itself from a Home Assistant backup.

See the [Kiosk Satellite remote API documentation][remote-api] for details.

[remote-api]: https://kiosksatellite.com/docs/remote-api/

## Weather screensaver and parcel tables

Kiosk Satellite's Home Assistant Dashboard screensaver captures the first tap
when double-tap dismissal is off. **Dim** keeps the Home Assistant page
touchable. The `browser.inject_js` setting in the snapshot listens for the
Dim saver to start and shows `/kitchen-weather/ambient` in the same WebView.
Kiosk Satellite applies adaptive brightness to the Dim level. Its separate
screensaver brightness switch does not control Dim mode.

After restoring the snapshot, check **Web Browsing → Inject JavaScript on the
HA dashboard** for the block beginning `// Kitchen weather on the live
dashboard while the native Dim saver is active.` Reload the kiosk page after
changing that field. The weather view's Home Assistant card still renders the
chips and tables. See the [dashboard map](../dashboards.md#kitchen-tablet).

To verify, let the tablet idle and tap each parcel chip once. Its table should
open. Tap **סגירה** to close the table and stay on the weather view. A tap on
the weather background should return to Kitchen Tablet controls.
