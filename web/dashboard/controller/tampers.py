#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/9 15:36
# @Author  : LoRexxar
# @File    : tamper.py
# @Contact : lorexxar@gmail.com
import os

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseNotFound
from django.views.generic import TemplateView
from django.views import View
from django.shortcuts import render, redirect
from django.db.models import Q

from Kunlun_M.settings import RULES_PATH
from web.index.models import Tampers


def _scan_tamper_files():
    """
    扫描文件系统获取所有 tamper（新版子目录 + 旧版根目录）。

    返回 [(name, language, filepath), ...] 按 name 排序。
    """
    tamper_base = os.path.join(RULES_PATH, 'tamper')
    results = []
    if not os.path.isdir(tamper_base):
        return results

    for entry in os.listdir(tamper_base):
        full = os.path.join(tamper_base, entry)
        if not os.path.isdir(full) or entry.startswith('_') or entry == '__pycache__':
            continue
        for fname in sorted(os.listdir(full)):
            if not fname.endswith('.py') or fname.startswith('_'):
                continue
            name = fname[:-3]
            results.append((name, entry, os.path.join(full, fname)))

    # 兼容：根目录旧版 tamper
    _SKIP_FILES = frozenset({'__init__.py', '_loader.py', '_compat.py'})
    for fname in sorted(os.listdir(tamper_base)):
        filepath = os.path.join(tamper_base, fname)
        if not os.path.isfile(filepath) or not fname.endswith('.py'):
            continue
        if fname in _SKIP_FILES or fname.startswith('_') or fname.startswith('demo'):
            continue
        name = fname[:-3]
        if not any(n == name for n, _, _ in results):
            results.append((name, 'legacy', filepath))

    results.sort(key=lambda x: x[0])
    return results


def _get_db_records_by_name(name):
    """从数据库获取指定 tamper_name 的所有记录"""
    return list(Tampers.objects.filter(tam_name=name))


class TamperListView(TemplateView):
    """展示所有tamper，按语言分组"""
    template_name = "dashboard/tampers/tampers_list.html"

    def get_context_data(self, **kwargs):
        context = super(TamperListView, self).get_context_data(**kwargs)

        file_tampers = _scan_tamper_files()

        # 按语言分组
        lang_order = ['php', 'java', 'python', 'go', 'nodejs', 'solidity', 'chromeext', 'legacy']
        lang_groups = {}
        for name, language, filepath in file_tampers:
            lang_groups.setdefault(language, []).append((name, filepath))

        # 按预定义顺序排列语言，未知语言放最后
        sorted_groups = []
        for lang in lang_order:
            if lang in lang_groups:
                sorted_groups.append((lang, lang_groups[lang]))
        for lang in sorted(lang_groups.keys()):
            if lang not in lang_order:
                sorted_groups.append((lang, lang_groups[lang]))

        context['lang_groups'] = sorted_groups
        return context


class TamperSourceJsonView(View):
    """返回所有 tamper 的源码，供前端 AJAX 加载"""
    @staticmethod
    @login_required
    def get(request):
        result = {}
        for name, lang, filepath in _scan_tamper_files():
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    result[name] = f.read()
            except Exception:
                result[name] = ''
        return JsonResponse(result)


class TamperDetailView(View):
    """展示 tamper 详情及源码"""

    @staticmethod
    @login_required
    def get(request, tamper_id):
        from Kunlun_M.settings import RULES_PATH

        tamper_name = None
        all_records = []

        try:
            int_id = int(tamper_id)
            tamper_record = Tampers.objects.filter(id=int_id).first()
            if tamper_record:
                tamper_name = tamper_record.tam_name
                all_records = list(Tampers.objects.filter(tam_name=tamper_name))
        except (ValueError, TypeError):
            pass

        if not tamper_name:
            file_tampers = _scan_tamper_files()
            for name, lang, fpath in file_tampers:
                if str(name) == str(tamper_id):
                    tamper_name = name
                    all_records = _get_db_records_by_name(name)
                    break

        if not tamper_name:
            return HttpResponseNotFound('Tamper Not Found.')

        source_code = None
        source_path = None

        tamper_base = os.path.join(RULES_PATH, 'tamper')
        if os.path.isdir(tamper_base):
            for lang_dir in os.listdir(tamper_base):
                full_dir = os.path.join(tamper_base, lang_dir)
                if os.path.isdir(full_dir) and not lang_dir.startswith('_') and lang_dir != '__pycache__':
                    candidate = os.path.join(full_dir, tamper_name + '.py')
                    if os.path.isfile(candidate):
                        try:
                            with open(candidate, 'r', encoding='utf-8', errors='replace') as f:
                                source_code = f.read()
                            source_path = os.path.relpath(candidate, RULES_PATH)
                        except Exception:
                            pass
                        break
            if not source_code:
                candidate = os.path.join(tamper_base, tamper_name + '.py')
                if os.path.isfile(candidate):
                    try:
                        with open(candidate, 'r', encoding='utf-8', errors='replace') as f:
                            source_code = f.read()
                        source_path = os.path.relpath(candidate, RULES_PATH)
                    except Exception:
                        pass

        data = {
            'tamper_name': tamper_name,
            'tamper_id': tamper_id,
            'records': all_records,
            'source_code': source_code,
            'source_path': source_path,
        }
        return render(request, 'dashboard/tampers/tamper_detail.html', data)
