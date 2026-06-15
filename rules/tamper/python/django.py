# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Django'
DEPENDENCIES = {'requirements': ['django'], 'pyproject': ['django']}


def detect(project_dir, language='python'):
    """检测是否为 Django 项目"""
    return (os.path.isfile(os.path.join(project_dir, 'manage.py'))
            or os.path.isfile(os.path.join(project_dir, 'settings.py'))
            or os.path.isfile(os.path.join(project_dir, 'wsgi.py')))


FILTER_FUNCTIONS = {
    # Django HTML 转义 / 安全 HTML 构造
    'django.utils.html.escape': [7000, 7008],
    'django.utils.html.format_html': [7000, 7008],
    'django.utils.html.format_html_join': [7000, 7008],
}

EXTRA_SINKS = [
    (".objects.raw(", [7002]),
    (".objects.extra(", [7002]),
    ("cursor().execute(", [7002]),
    ("render(", [7006]),
    ("render_to_string(", [7006]),
    ("HttpResponseRedirect(", [7010]),
    ("redirect(", [7010]),
    ("django.template.Template(", [7006]),
]

CONTROLLED_SOURCES = [
    'request.GET',
    'request.POST',
    'request.FILES',
    'request.body',
    'request.META',
    'request.COOKIES',
    '@request.GET',
    'self.kwargs',
    'self.args',
    'request.get_full_path',
    'request.get_host',
]
