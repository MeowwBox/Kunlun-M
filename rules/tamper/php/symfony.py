# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Symfony'
DEPENDENCIES = {'composer': ['symfony/framework-bundle', 'symfony/symfony']}


def detect(project_dir, language='php'):
    """检测是否为 Symfony 项目"""
    return os.path.isfile(os.path.join(project_dir, 'config', 'bundles.php'))


FILTER_FUNCTIONS = {
    'escape': {'safe_for': [1000, 10001, 10002]},
    'htmlspecialchars': {'safe_for': [1000]},
}

CONTROLLED_SOURCES = [
    '$request->get',
    '$request->request->get',
    '$request->query->get',
    '$request->headers->get',
    '$request->getContent',
    'Request::get',
]

EXTRA_SINKS = [
    ("->createQuery(", [1004]),
    ("->executeQuery(", [1004]),
    ("Connection::executeQuery(", [1004]),
]
