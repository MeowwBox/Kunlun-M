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
        # entry 是语言目录
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
        # 检查是否为旧版格式（同名的已在语言子目录中就跳过）
        if not any(n == name for n, _, _ in results):
            results.append((name, 'legacy', filepath))

    results.sort(key=lambda x: x[0])
    return results


def _get_db_records_by_name(name):
    """从数据库获取指定 tamper_name 的所有记录"""
    return list(Tampers.objects.filter(tam_name=name))


class TamperListView(TemplateView):
    """展示所有tamper"""
    template_name = "dashboard/tampers/tampers_list.html"

    def get_context_data(self, **kwargs):
        context = super(TamperListView, self).get_context_data(**kwargs)
        tampers_details = {}

        # 以文件系统为主数据源，确保展示所有实际存在的 tamper
        file_tampers = _scan_tamper_files()

        # 先收集所有数据库记录
        db_records = {}
        for t in Tampers.objects.all():
            db_records.setdefault(t.tam_name, []).append(t)

        i = 1
        for name, language, filepath in file_tampers:
            detail = {
                'id': i,
                'FilterFunction': {},
                'ControlledSources': [],
                'ExtraSinks': [],
                'language': language,
                'filepath': filepath,
            }
            i += 1

            # 尝试从数据库补充信息
            records = db_records.get(name, [])
            for t in records:
                if t.tam_type == 'Filter-Function':
                    detail['FilterFunction'][t.tam_key] = t.tam_value
                elif t.tam_type == 'Controlled-Sources':
                    detail['ControlledSources'].append(t.tam_value)
                elif t.tam_type == 'Extra-Sinks':
                    detail['ExtraSinks'].append((t.tam_key, t.tam_value))
                elif t.tam_type == 'Input-Control':
                    detail['ControlledSources'].append(t.tam_value)

            # 如果数据库没有，从文件直接加载
            if not records and not detail['FilterFunction']:
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location('_tmp_{}'.format(name), filepath)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        ff = getattr(mod, 'FILTER_FUNCTIONS', None)
                        if ff:
                            for k, v in ff.items():
                                if isinstance(v, dict):
                                    detail['FilterFunction'][k] = str(v.get('safe_for', []))
                                elif isinstance(v, list):
                                    detail['FilterFunction'][k] = str(v)
                        cs = getattr(mod, 'CONTROLLED_SOURCES', [])
                        if cs:
                            detail['ControlledSources'] = [str(s) for s in cs]
                        es = getattr(mod, 'EXTRA_SINKS', [])
                        if es:
                            detail['ExtraSinks'] = [(s[0], str(s[1])) for s in es]
                except Exception:
                    pass

            tampers_details[name] = detail

        context['tampers'] = tampers_details
        return context


class TamperDetailView(View):
    """展示 tamper 详情及源码"""

    @staticmethod
    @login_required
    def get(request, tamper_id):
        from Kunlun_M.settings import RULES_PATH

        # 支持两种查找方式：
        # 1. 按 id 查找（数据表主键，旧链接兼容）
        # 2. 如果 id 找不到，尝试按文件名查找
        tamper_name = None
        all_records = []

        # 先尝试当作数字 id 查询
        try:
            int_id = int(tamper_id)
            tamper_record = Tampers.objects.filter(id=int_id).first()
            if tamper_record:
                tamper_name = tamper_record.tam_name
                all_records = list(Tampers.objects.filter(tam_name=tamper_name))
        except (ValueError, TypeError):
            pass

        if not tamper_name:
            # id 没找到或不是数字，尝试按文件名查找
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

        # 从文件系统搜索真实源文件
        tamper_base = os.path.join(RULES_PATH, 'tamper')
        if os.path.isdir(tamper_base):
            # 先搜语言子目录
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
            # 兼容：根目录旧版 tamper
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
