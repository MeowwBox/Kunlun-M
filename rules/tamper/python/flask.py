# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Flask'
DEPENDENCIES = {'requirements': ['flask'], 'pyproject': ['flask']}


def detect(project_dir, language='python'):
    """检测是否为 Flask 项目"""
    app_py = os.path.join(project_dir, 'app.py')
    if os.path.isfile(app_py):
        with open(app_py, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if 'flask' in content.lower():
                return True
    return False


FILTER_FUNCTIONS = {
    # HTML 转义 / 安全输出（Flask 内置 escape 别名）
    'flask.escape': [7000, 7008],
    # 安全 URL 生成（不会产生开放重定向）
    'url_for': [7010],
    # 安全 JSON 输出（Content-Type 为 application/json）
    'jsonify': [7000, 7008],
}

EXTRA_SINKS = [
    ("render_template_string(", [7006]),
    ("render_template(", [7006]),
    ("render_template_list(", [7006]),
    ("redirect(", [7010]),
    ("send_file(", [7005]),
    ("send_from_directory(", [7005, 7009]),
]

CONTROLLED_SOURCES = [
    'flask.request',
    'request.query_string',
    'request.cookies',
    'session',
]
