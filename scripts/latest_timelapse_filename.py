#!/usr/bin/env python3
"""Print the basename of the newest MP4 file in Home Assistant's www folder."""

import os
import stat as stat_module


ROOT = "/config/www"
latest = None

for directory, _, filenames in os.walk(ROOT, followlinks=False):
    for filename in filenames:
        if not filename.endswith(".mp4"):
            continue
        path = os.path.join(directory, filename)
        try:
            metadata = os.stat(path, follow_symlinks=False)
        except OSError:
            continue
        if not stat_module.S_ISREG(metadata.st_mode) or (latest is not None and metadata.st_mtime_ns <= latest[0]):
            continue
        latest = (metadata.st_mtime_ns, filename)

if latest is not None:
    print(latest[1])
