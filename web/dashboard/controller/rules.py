#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/5 10:41
# @Author  : LoRexxar
# @File    : rules.py
# @Contact : lorexxar@gmail.com
import os

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from django.http import HttpResponseNotFound
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView

from web.index.models import Rules
from Kunlun_M.settings import RULES_PATH


class RuleListView(TemplateView):
    """展示所有规则"""
    template_name = "dashboard/rules/rules_list.html"

    def get_context_data(self, **kwargs):
        context = super(RuleListView, self).get_context_data(**kwargs)

        rows = Rules.objects.filter()
        context['rules'] = rows

        return context


class RuleDetailView(View):
    """展示规则细节"""

    @staticmethod
    @login_required
    def get(request, rule_id):
        row = Rules.objects.filter(id=rule_id).first()

        if not row:
            return HttpResponseNotFound('Rule Not Found.')

        source_code = None
        # 优先从源文件读取真实代码
        if row.language and row.svid:
            rule_file = os.path.join(RULES_PATH, row.language, 'CVI_{}.py'.format(row.svid))
            if os.path.isfile(rule_file):
                try:
                    with open(rule_file, 'r', encoding='utf-8', errors='replace') as f:
                        source_code = f.read()
                except Exception:
                    pass

        data = {
            'rule': row,
            'source_code': source_code,
        }
        return render(request, 'dashboard/rules/rules_detail.html', data)
