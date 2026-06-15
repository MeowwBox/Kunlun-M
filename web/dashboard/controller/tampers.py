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
    """展示当前任务细节"""

    @staticmethod
    @login_required
    def get(request, task_id):
        tampers = Tampers.objects.all()

        if not tampers:
            return HttpResponseNotFound('Task Not Found.')
        else:
            data = {
                'tampers': tampers
            }
            return render(request, 'dashboard/tasks/task_detail.html', data)
