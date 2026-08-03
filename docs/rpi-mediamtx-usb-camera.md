# Raspberry Pi USB Camera → RTSP with MediaMTX

This document describes a **full, from-scratch, reboot-safe setup** for streaming one or more USB cameras from a Raspberry Pi using **FFmpeg** and **MediaMTX**.

It includes **installation**, **configuration**, and **multi-camera expansion**.

---

## Tested Environment

- Raspberry Pi OS (64-bit)
- Raspberry Pi 3B / 4
- Architecture: **arm64 (aarch64)**
- MediaMTX **v1.15.5**
- FFmpeg (Debian repository)

---

## 1. System Preparation

Update the system and install required packages:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y   ffmpeg   v4l-utils   ca-certificates   curl
```

Verify camera detection:

```bash
ls -l /dev/video*
v4l2-ctl --list-devices
```

---

## 2. User Permissions

Ensure your user exists and can access video devices:

```bash
id ohadbenita
sudo usermod -aG video ohadbenita
```

Reboot once if you just added the group:

```bash
sudo reboot
```

---

## 3. Install MediaMTX (v1.15.5, arm64)

Download and install the MediaMTX binary:

```bash
cd /tmp

curl -L -o mediamtx_v1.15.5_linux_arm64.tar.gz   https://github.com/bluenviron/mediamtx/releases/download/v1.15.5/mediamtx_v1.15.5_linux_arm64.tar.gz

tar xzf mediamtx_v1.15.5_linux_arm64.tar.gz

sudo install -m 0755 mediamtx /usr/local/bin/mediamtx
```

Verify installation:

```bash
/usr/local/bin/mediamtx --version
```

---

## 4. MediaMTX Configuration

Create configuration directory and file:

```bash
sudo mkdir -p /etc/mediamtx
sudo nano /etc/mediamtx/mediamtx.yml
```

```yaml
logLevel: info

rtsp: yes
rtspAddress: :8554

rtmp: no
hls: no
webrtc: no
srt: no

api: no
metrics: no
pprof: no

paths:
  crealityNebula: {}
```

> ⚠️ When `paths:` is present, every RTSP path must be explicitly defined.

---

## 5. MediaMTX systemd Service

Create the service:

```bash
sudo nano /etc/systemd/system/mediamtx.service
```

```ini
[Unit]
Description=MediaMTX (RTSP server)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ohadbenita
Group=ohadbenita
ExecStart=/usr/local/bin/mediamtx /etc/mediamtx/mediamtx.yml
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mediamtx
systemctl status mediamtx --no-pager
```

---

## 6. FFmpeg Publisher (Camera 1)

Publishes `/dev/video0` → `/crealityNebula`

```bash
sudo nano /etc/systemd/system/ffmpeg-usb-rtsp.service
```

```ini
[Unit]
Description=FFmpeg USB camera RTSP publisher
After=network-online.target mediamtx.service
Wants=network-online.target
Requires=mediamtx.service

[Service]
Type=simple
User=ohadbenita
Group=ohadbenita
ExecStartPre=/bin/sleep 5

ExecStart=/usr/bin/ffmpeg   -f v4l2 -framerate 30 -video_size 1280x720   -i /dev/video0   -c:v libx264   -pix_fmt yuv420p   -profile:v baseline   -preset ultrafast -tune zerolatency   -f rtsp -rtsp_transport tcp   rtsp://127.0.0.1:8554/crealityNebula

Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ffmpeg-usb-rtsp
systemctl status ffmpeg-usb-rtsp --no-pager
```

---

## 7. Verification

```bash
ffplay -rtsp_transport tcp rtsp://127.0.0.1:8554/crealityNebula
```

From another machine:

```text
rtsp://<PI_IP>:8554/crealityNebula
```

---

## 8. Adding Another Camera

1. Identify the new device:

```bash
ls -l /dev/video*
```

1. Add a path:

```yaml
paths:
  crealityNebula: {}
  camera2: {}
```

Restart MediaMTX:

```bash
sudo systemctl restart mediamtx
```

1. Create a second FFmpeg service:

```bash
sudo nano /etc/systemd/system/ffmpeg-usb-rtsp-camera2.service
```

```ini
[Unit]
Description=FFmpeg USB camera2 RTSP publisher
After=network-online.target mediamtx.service
Wants=network-online.target
Requires=mediamtx.service

[Service]
Type=simple
User=ohadbenita
Group=ohadbenita
ExecStartPre=/bin/sleep 5

ExecStart=/usr/bin/ffmpeg   -f v4l2 -framerate 15 -video_size 1280x720   -i /dev/video2   -c:v libx264   -pix_fmt yuv420p   -profile:v baseline   -preset ultrafast -tune zerolatency   -f rtsp -rtsp_transport tcp   rtsp://127.0.0.1:8554/camera2

Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ffmpeg-usb-rtsp-camera2
```

---

## 9. Performance Notes (Pi 3B)

- 1× camera @ 720p30 OK
- 2× cameras @ 720p15 recommended
- Reduce FPS or resolution if artifacts appear
- Prefer hardware encoding (`h264_v4l2m2m`) if available

---

## 10. Troubleshooting

| Symptom | Cause |
| ------- | ----- |
| 400 Bad Request | RTSP path not defined |
| Green blocks | CPU overloaded |
| Restart loop | Camera not ready / permissions |
| No stream after reboot | FFmpeg service not enabled |

---
