# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Drupal'
DEPENDENCIES = {'composer': ['drupal/core', 'drupal/drupal']}


def detect(project_dir, language='php'):
    """检测是否为 Drupal 项目"""
    return os.path.isfile(os.path.join(project_dir, 'core', 'lib', 'Drupal.php'))


FILTER_FUNCTIONS = {
    'check_plain': {'safe_for': [1000, 10001, 10002]},
    'drupal_html_class': {'safe_for': [1000]},
    'UrlHelper::stripDangerousProtocols': {'safe_for': [1000]},
}

CONTROLLED_SOURCES = [
    '\\Drupal::request()->get',
    '\\Drupal::requestStack()->getCurrentRequest()->get',
]

EXTRA_SINKS = [
    ('\\Drupal::database()->query', [1004]),
    ('\\Drupal::database()->select', [1004]),
]
