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
    'esc_url': {'safe_for': [1000]},
    'esc_js': {'safe_for': [1000]},
    'esc_html': {'safe_for': [1000, 10001, 10002]},
    'esc_attr': {'safe_for': [1000, 10001, 10002]},
    'esc_textarea': {'safe_for': [1000, 10001, 10002]},
    'tag_escape': {'safe_for': [1000]},
    'esc_sql': {'safe_for': [1000]},
    '_real_escape': {'safe_for': [1000]},
}

CONTROLLED_SOURCES = []

EXTRA_SINKS = [
    ('$wpdb->query', [1004]),
    ('$wpdb->get_results', [1004]),
    ('$wpdb->get_var', [1004]),
    ('$wpdb->get_row', [1004]),
    ('$wpdb->prepare', []),
]
