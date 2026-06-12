# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'WordPress'
DEPENDENCIES = {}


def detect(project_dir, language='php'):
    """检测是否为 WordPress 项目"""
    return (os.path.exists(os.path.join(project_dir, 'wp-config.php'))
            or os.path.isdir(os.path.join(project_dir, 'wp-content'))
            or os.path.isdir(os.path.join(project_dir, 'wp-includes')))


FILTER_FUNCTIONS = {
    'esc_url': [1000],
    'esc_js': [1000],
    'esc_html': [1000, 10001, 10002],
    'esc_attr': [1000, 10001, 10002],
    'esc_textarea': [1000, 10001, 10002],
    'tag_escape': [1000],
    'esc_sql': [1000],
    '_real_escape': [1000],
}

CONTROLLED_SOURCES = []
