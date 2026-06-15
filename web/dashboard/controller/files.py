#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import json

from django.http import JsonResponse, HttpResponseNotFound
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

from web.index.models import ScanTask, Project


class ProjectFilesView(TemplateView):
    """项目文件管理器"""
    template_name = "dashboard/projects/project_files.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = kwargs['project_id']
        project = Project.objects.filter(id=project_id).first()
        if not project:
            return context

        # 优先取最新有 source_dir 的任务（上传扫描解压目录）
        task = ScanTask.objects.filter(
            project_id=project_id
        ).exclude(source_dir__isnull=True).exclude(source_dir='').order_by('-id').first()
        if not task:
            task = ScanTask.objects.filter(project_id=project_id).order_by('-id').first()

        source_root = task.source_dir or task.target_path or '' if task else ''
        context['project'] = project
        context['source_root'] = source_root
        return context


class ProjectFilesApiView(View):
    """AJAX 目录浏览 — 返回子目录/文件列表"""

    @staticmethod
    def get(request, project_id):
        req_dir = request.GET.get('dir', '')
        root = request.GET.get('root', '')

        if not root:
            task = ScanTask.objects.filter(project_id=project_id).order_by('-id').first()
            root = (task.source_dir or task.target_path or '') if task else ''
            if not root:
                return JsonResponse({"entries": []})

        base = os.path.normpath(root)
        target = os.path.normpath(os.path.join(root, req_dir)) if req_dir else base

        # 路径遍历防护
        if not (target == base or target.startswith(base + os.sep)):
            return JsonResponse({"error": "forbidden"}, status=403)
        if not os.path.isdir(target):
            return JsonResponse({"entries": []})

        entries = []
        try:
            for name in sorted(os.listdir(target)):
                if name.startswith('.') or name == '__pycache__':
                    continue
                full = os.path.join(target, name)
                is_dir = os.path.isdir(full)
                if is_dir:
                    try:
                        child_count = len([c for c in os.listdir(full) if not c.startswith('.')])
                    except OSError:
                        child_count = -1
                else:
                    child_count = 0
                entries.append({
                    "name": name,
                    "path": os.path.relpath(full, base).replace('\\', '/'),
                    "is_dir": is_dir,
                    "size": os.path.getsize(full) if not is_dir else child_count,
                })
        except PermissionError:
            pass

        # 目录在前，文件在后
        entries.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return JsonResponse({"entries": entries})


class ProjectFileContentApiView(View):
    """AJAX 文件内容 — 支持行高亮"""

    @staticmethod
    def get(request, project_id):
        req_file = request.GET.get('file', '')
        highlight = request.GET.get('lineno', '')
        root = request.GET.get('root', '')

        if not root:
            task = ScanTask.objects.filter(project_id=project_id).order_by('-id').first()
            root = (task.source_dir or task.target_path or '') if task else ''

        abs_path = os.path.normpath(os.path.join(root, req_file)) if root and req_file else ''
        base = os.path.normpath(root) if root else ''

        if not abs_path or not base:
            return JsonResponse({"error": "no source"}, status=404)
        if not (abs_path == base or abs_path.startswith(base + os.sep)):
            return JsonResponse({"error": "forbidden"}, status=403)
        if not os.path.isfile(abs_path):
            return JsonResponse({"error": "not found"}, status=404)

        size = os.path.getsize(abs_path)
        if size > 1024 * 1024:
            return JsonResponse({"error": "file too large (>1MB)"}, status=413)

        try:
            with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except OSError:
            return JsonResponse({"error": "read error"}, status=500)

        lines = content.split('\n')

        lineno = None
        if highlight:
            try:
                lineno = int(highlight)
            except (ValueError, TypeError):
                pass

        return JsonResponse({
            "file": req_file,
            "lines": lines,
            "total_lines": len(lines),
            "highlight": lineno,
        })
