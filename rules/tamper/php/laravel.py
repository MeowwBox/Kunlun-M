# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Laravel'
DEPENDENCIES = {'composer': ['laravel/framework']}


def detect(project_dir, language='php'):
    """检测是否为 Laravel 项目"""
    return (os.path.isfile(os.path.join(project_dir, 'app', 'Http', 'Kernel.py'))
            or os.path.isfile(os.path.join(project_dir, 'routes', 'web.php'))
            or os.path.isfile(os.path.join(project_dir, 'artisan')))


FILTER_FUNCTIONS = {
    'e()': {'safe_for': [1000, 10001, 10002]},
    'csrf_field': {'safe_for': []},
    'csrf_token': {'safe_for': []},
}

EXTRA_SINKS = [
    ("DB::raw", [1004]),
    ("DB::select", [1004]),
    ("DB::statement", [1004]),
    ("DB::unprepared", [1004]),
]

CONTROLLED_SOURCES = [
    'request()->input',
    'request()->get',
    'request()->post',
    'request()->query',
    'request()->cookie',
    '$request->input',
    '$request->query',
    '$request->post',
    '$request->cookie',
    'request()->header',
    '$request->header',
    '$request->ip',
    '$request->userAgent',
    'Request::get',
    'Request::input',
    'Request::query',
    'Request::post',
    'Request::cookie',
    'Request::header',
    'request()',
    '$request',
    'input()',
    'old()',
]
