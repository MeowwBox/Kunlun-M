#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/26 16:38
# @Author  : LoRexxar
# @File    : views.py
# @Contact : lorexxar@gmail.com

import os
import ast
import codecs
import json
import csv
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from web.index.controller import login_or_token_required, api_token_required
from web.index.models import ScanTask, ScanResultTask, Rules, Tampers, NewEvilFunc, get_resultflow_class
from web.index.models import get_and_check_scantask_project_id, get_and_check_scanresult
from utils.utils import show_context

from Kunlun_M.settings import LOGS_PATH


def index(request):
    return HttpResponse("Nothing here.")


@login_or_token_required
def tasklog(req, task_id):
    task = ScanTask.objects.filter(id=task_id).first()
    visit_token = ""

    if 'token' in req.GET:
        visit_token = req.GET['token']

    # check task是否存在
    if not task:
        return redirect("dashboard:tasks_list")

    project_id = get_and_check_scantask_project_id(task_id)

    srts = get_and_check_scanresult(task_id).objects.filter(scan_project_id=project_id, is_active=1)
    nefs = NewEvilFunc.objects.filter(project_id=project_id)

    ResultFlow = get_resultflow_class(task_id)
    rfs = ResultFlow.objects.all()

    task.parameter_config = " ".join(ast.literal_eval(task.parameter_config)).replace('\\', '/')
    resultflowdict = {}

    for rf in rfs:

        # 加入漏洞有效检查，可能已被删除或处理
        # 组件漏洞不显示
        if rf.node_type == "sca_scan":
            continue

        r = get_and_check_scanresult(task_id).objects.filter(id=rf.vul_id, is_active=1).first()
        if not r:
            continue

        if rf.vul_id not in resultflowdict:
            resultflowdict[rf.vul_id] = {
                'id': rf.vul_id,
                'flow': [],
            }

        rfdict = {
            'type': rf.node_type,
            'content': rf.node_content,
            'path': rf.node_path,
            'lineno': rf.node_lineno,
            'details': rf.node_source
        }

        resultflowdict[rf.vul_id]['flow'].append(rfdict)

    # 扫描结果
    data = {
        "task": task,
        "taskresults": srts,
        "newevilfuncs": nefs,
        "resultflowdict": resultflowdict,
        'visit_token': visit_token
    }
    return render(req, 'backend/tasklog.html', data)


@login_or_token_required
def tasklogtail(req, task_id):
    task = ScanTask.objects.filter(id=task_id).first()
    if not task:
        return JsonResponse({"code": 404, "status": False, "message": "Task not found."})

    offset = 0
    if "offset" in req.GET:
        try:
            offset = int(req.GET["offset"])
        except Exception:
            offset = 0
    if offset < 0:
        offset = 0

    log_path = os.path.join(LOGS_PATH, "ScanTask_{}.log".format(task_id))
    if not os.path.exists(log_path):
        return JsonResponse({"code": 200, "status": True, "message": {"offset": offset, "data": "", "eof": True}})

    max_bytes = 20000
    with open(log_path, "rb") as f:
        f.seek(offset)
        data = f.read(max_bytes)
        new_offset = f.tell()

    text = ""
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = ""

    eof = len(data) < max_bytes
    return JsonResponse({"code": 200, "status": True, "message": {"offset": new_offset, "data": text, "eof": eof}})


@login_or_token_required
def debuglog(req, task_id):

    task = ScanTask.objects.filter(id=task_id).first()
    visit_token = ""

    if 'token' in req.GET:
        visit_token = req.GET['token']

    # check task是否存在
    if not task:
        return redirect("dashboard:tasks_list")

    debuglog_filename = os.path.join(LOGS_PATH, 'ScanTask_{}.log'.format(task_id))

    if not os.path.exists(debuglog_filename):
        return HttpResponse("Ooooops, Log file not found...")

    f = codecs.open(debuglog_filename, "r", encoding='utf-8', errors='ignore')
    debuglog_content = f.read()
    f.close()

    data = {
        "task": task,
        "debuglog_content": debuglog_content,
        'visit_token': visit_token
    }
    return render(req, 'backend/debuglog.html', data)


@login_or_token_required
def downloadlog(req, task_id):
    task = ScanTask.objects.filter(id=task_id).first()

    # check task是否存在
    if not task:
        return redirect("dashboard:tasks_list")

    debuglog_filename = os.path.join(LOGS_PATH, 'ScanTask_{}.log'.format(task_id))

    if not os.path.exists(debuglog_filename):
        return HttpResponse("Ooooops, Log file not found...")

    f = codecs.open(debuglog_filename, "r", encoding='utf-8', errors='ignore')
    debuglog_content = f.read()
    f.close()

    path_to_file = debuglog_filename
    response = HttpResponse(debuglog_content, content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename=ScanTask_%s' % task_id + ".log"
    response['X-Sendfile'] = path_to_file
    return response


@login_or_token_required
def exportresult(req, task_id):
    task = ScanTask.objects.filter(id=task_id).first()
    if not task:
        return HttpResponse("Task not found.", status=404)

    fmt = (req.GET.get("format", "json") or "json").lower()
    project_id = get_and_check_scantask_project_id(task_id)
    rows = list(get_and_check_scanresult(task_id).objects.filter(scan_project_id=project_id, is_active=1).values())

    if fmt == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = "attachment; filename=ScanTask_{}_result.csv".format(task_id)
        if not rows:
            return resp

        fieldnames = list(rows[0].keys())
        w = csv.DictWriter(resp, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
        return resp

    resp = JsonResponse({"code": 200, "status": True, "message": rows})
    resp["Content-Disposition"] = "attachment; filename=ScanTask_{}_result.json".format(task_id)
    return resp


@api_token_required
def uploadlog(req):
    if "file" not in req.FILES:
        return HttpResponse("Ooooops, bad request...")

    logfile = req.FILES.get("file", None)

    logfile_name = logfile.name

    if os.path.exists(os.path.join(LOGS_PATH, logfile_name)):
        return HttpResponse("Ooooops, log file {} exist...".format(logfile_name))

    with open(os.path.join(LOGS_PATH, logfile_name), 'wb') as f:
        for chunk in logfile.chunks():
            f.write(chunk)

    return HttpResponse("Success")
