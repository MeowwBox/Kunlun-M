import os
import shutil
from datetime import timedelta

from django.utils import timezone

from Kunlun_M import settings
from web.index.models import ScanTask


def cleanup_packages():
    retention_days = int(getattr(settings, "WEB_PACKAGE_RETENTION_DAYS", 7) or 7)
    if retention_days <= 0:
        return 0

    base = getattr(settings, "PACKAGE_PATH", None)
    if not base or not os.path.isdir(base):
        return 0

    threshold = timezone.now() - timedelta(days=retention_days)
    removed = 0

    for name in os.listdir(base):
        if not name.isdigit():
            continue
        task_id = int(name)
        t = ScanTask.objects.filter(id=task_id).first()
        if not t:
            continue
        if int(t.is_finished) not in [0, 1]:
            continue
        ft = t.finished_at or t.last_scan_time or t.created_at
        if not ft or ft > threshold:
            continue

        p = os.path.join(base, name)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
            removed += 1

    return removed

