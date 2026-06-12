# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Roundcube'
DEPENDENCIES = {'composer': ['roundcube/roundcubemail']}


def detect(project_dir, language='php'):
    """检测是否为 Roundcube 项目"""
    return os.path.isfile(os.path.join(project_dir, 'program', 'include', 'iniset.php'))


FILTER_FUNCTIONS = {
    'rcube_utils::rep_specialchars_output': [1000, 10001, 10002],
}

CONTROLLED_SOURCES = [
    'rcube_utils::get_input_value',
    'rcube_utils::get_request_header',
    'rcube_utils::get_request_param',
]
