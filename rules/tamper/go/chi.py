# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Chi'
DEPENDENCIES = {'gomod': ['github.com/go-chi/chi']}


def detect(project_dir, language='go'):
    """检测是否为 Chi 项目"""
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'r.URL.Query',
    'chi.URLParam',
    'chi.URLParamFromCtx',
]

EXTRA_SINKS = [
    ("http.Redirect(", [8013]),
]
