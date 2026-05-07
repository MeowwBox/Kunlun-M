#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/2/23 16:38
# @Author  : LoRexxar
# @File    : views.py
# @Contact : lorexxar@gmail.com


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.conf import settings
from web.index.models import ScanTask, Project
from web.index.models import get_and_check_scantask_project_id

from utils.utils import del_sensitive_for_config
from web.index.scan_dispatcher import try_dispatch

from Kunlun_M.settings import API_TOKEN
import os


@login_required
def index(req):

    tasks = ScanTask.objects.all().order_by("-id")[:100]
    for task in tasks:
        task.is_finished = int(task.is_finished)
        task.parameter_config = del_sensitive_for_config(task.parameter_config)

        project_id = get_and_check_scantask_project_id(task.id)
        project = Project.objects.filter(id=project_id).first()

        task.project_name = project.project_name

    data = {'tasks': tasks}

    return render(req, 'dashboard/index.html', data)


@login_required
def docs(req):
    default_path = req.GET.get("path") or "README.md"
    return render(req, 'dashboard/docs.html', {"default_doc_path": default_path})


def _docs_root():
    return os.path.join(settings.BASE_DIR, "docs")


def _normalize_doc_path(p):
    if not p:
        return None
    p = str(p).strip().replace("\\", "/")
    if not p or p.startswith("/"):
        return None
    if "://" in p:
        return None
    p = os.path.normpath(p).replace("\\", "/")
    if p == "." or p.startswith("../") or p == "..":
        return None
    if not p.lower().endswith(".md"):
        return None
    return p


def _safe_doc_abspath(rel_path):
    rel_path = _normalize_doc_path(rel_path)
    if not rel_path:
        return None, None
    root = os.path.abspath(_docs_root())
    abs_path = os.path.abspath(os.path.join(root, rel_path))
    if not (abs_path == root or abs_path.startswith(root + os.sep)):
        return None, None
    return rel_path, abs_path


@login_required
def docs_api_list(req):
    root = _docs_root()
    if not os.path.isdir(root):
        return JsonResponse({"status": "ok", "files": []})

    files = []
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d and not d.startswith(".")]
        for fn in filenames:
            if not fn or fn.startswith("."):
                continue
            if not fn.lower().endswith(".md"):
                continue
            abs_path = os.path.join(dirpath, fn)
            rel = os.path.relpath(abs_path, root).replace("\\", "/")
            rel = _normalize_doc_path(rel)
            if not rel:
                continue
            files.append({"path": rel, "name": fn})
            count += 1
            if count >= 200:
                break
        if count >= 200:
            break

    files.sort(key=lambda x: x["path"].lower())
    return JsonResponse({"status": "ok", "files": files})


@login_required
def docs_api_file(req):
    rel, abs_path = _safe_doc_abspath(req.GET.get("path"))
    if not abs_path or not os.path.isfile(abs_path):
        return JsonResponse({"status": "error", "message": "not found"}, status=404)

    try:
        size = os.path.getsize(abs_path)
    except OSError:
        return JsonResponse({"status": "error", "message": "not found"}, status=404)

    if size > 512 * 1024:
        return JsonResponse({"status": "error", "message": "file too large"}, status=413)

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return JsonResponse({"status": "error", "message": "not found"}, status=404)

    return JsonResponse({"status": "ok", "path": rel, "content": content})


@login_required
def docs_raw(req):
    rel, abs_path = _safe_doc_abspath(req.GET.get("path"))
    if not abs_path or not os.path.isfile(abs_path):
        return HttpResponse("not found", status=404, content_type="text/plain; charset=utf-8")

    try:
        size = os.path.getsize(abs_path)
    except OSError:
        return HttpResponse("not found", status=404, content_type="text/plain; charset=utf-8")

    if size > 512 * 1024:
        return HttpResponse("file too large", status=413, content_type="text/plain; charset=utf-8")

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return HttpResponse("not found", status=404, content_type="text/plain; charset=utf-8")

    resp = HttpResponse(content, content_type="text/markdown; charset=utf-8")
    resp["Content-Disposition"] = f'inline; filename="{os.path.basename(rel)}"'
    return resp


@login_required
def userinfo(req):

    data = {
        "apitoken": API_TOKEN
    }

    return render(req, 'dashboard/userinfo.html', data)


@login_required
def overview(req):
    try_dispatch()
    tasks = ScanTask.objects.all().order_by("-id")[:200]

    status_count = {
        "success": 0,
        "running": 0,
        "error": 0,
        "other": 0,
    }

    latest_task = None
    latest_scan_time = None

    for task in tasks:
        task_status = int(task.is_finished)
        if task_status == 1:
            status_count["success"] += 1
        elif task_status == 2:
            status_count["running"] += 1
        elif task_status in [0, -1]:
            status_count["error"] += 1
        else:
            status_count["other"] += 1

        if latest_scan_time is None and task.last_scan_time:
            latest_scan_time = timezone.localtime(
                task.last_scan_time,
                timezone.get_fixed_timezone(8 * 60)
            ).strftime("%Y-%m-%d %H:%M:%S")
            latest_task = {
                "id": task.id,
                "task_name": task.task_name,
                "target_path": task.target_path
            }

    return JsonResponse({
        "status": "ok",
        "count": len(tasks),
        "task_status": status_count,
        "latest_scan_time": latest_scan_time,
        "latest_task": latest_task
    })


