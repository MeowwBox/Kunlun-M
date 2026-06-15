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


class TamperListView(TemplateView):
    """展示所有tamper"""
    template_name = "dashboard/tampers/tampers_list.html"

    def get_context_data(self, **kwargs):
        context = super(TamperListView, self).get_context_data(**kwargs)
        tampers_details = {}

        ts = Tampers.objects.all()
        i = 1

        for t in ts:
            if t.tam_name not in tampers_details:
                tampers_details[t.tam_name] = {
                    'id': i,
                    'FilterFunction': {},
                    'ControlledSources': [],
                    'ExtraSinks': [],
                    'language': '',
                }
                i += 1

            if t.tam_type == 'Filter-Function':
                tampers_details[t.tam_name]['FilterFunction'][t.tam_key] = t.tam_value
            elif t.tam_type == 'Controlled-Sources':
                tampers_details[t.tam_name]['ControlledSources'].append(t.tam_value)
            elif t.tam_type == 'Extra-Sinks':
                tampers_details[t.tam_name]['ExtraSinks'].append((t.tam_key, t.tam_value))
            elif t.tam_type == 'Input-Control':  # 旧数据兼容
                tampers_details[t.tam_name]['ControlledSources'].append(t.tam_value)

        # 从文件系统获取语言映射
        tamper_base = os.path.join(RULES_PATH, 'tamper')
        if os.path.isdir(tamper_base):
            for lang_dir in os.listdir(tamper_base):
                full = os.path.join(tamper_base, lang_dir)
                if os.path.isdir(full) and not lang_dir.startswith('_') and lang_dir != '__pycache__':
                    for fname in os.listdir(full):
                        if fname.endswith('.py') and not fname.startswith('_'):
                            name = fname[:-3]
                            if name in tampers_details:
                                tampers_details[name]['language'] = lang_dir

        context['tampers'] = tampers_details

        return context


class TamperDetailView(View):
    """展示 tamper 详情及源码"""

    @staticmethod
    @login_required
    def get(request, tamper_id):
        from Kunlun_M.settings import RULES_PATH

        # tamper_id 是数据表 id，回溯到 tamper 名称
        tamper_record = Tampers.objects.filter(id=tamper_id).first()
        if not tamper_record:
            return HttpResponseNotFound('Tamper Not Found.')

        tamper_name = tamper_record.tam_name
        all_records = Tampers.objects.filter(tam_name=tamper_name)

        source_code = None
        source_path = None

        # 从文件系统搜索真实源文件
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

        data = {
            'tamper_name': tamper_name,
            'tamper_id': tamper_id,
            'records': all_records,
            'source_code': source_code,
            'source_path': source_path,
        }
        return render(request, 'dashboard/tampers/tamper_detail.html', data)
