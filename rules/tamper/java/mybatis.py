# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'MyBatis'
DEPENDENCIES = {'pom': ['mybatis', 'mybatis-spring']}


def detect(project_dir, language='java'):
    """检测是否为 MyBatis 项目"""
    pom_path = os.path.join(project_dir, 'pom.xml')
    if os.path.isfile(pom_path):
        try:
            with open(pom_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if 'mybatis' in content.lower():
                    return True
        except IOError:
            pass
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    '@Param',
    '@Mapper',
]

EXTRA_SINKS = [
    ('${', [6031]),
    # MyBatis dynamic SQL provider annotations
    ("@SelectProvider", [6031]),
    ("@InsertProvider", [6031]),
    ("@UpdateProvider", [6031]),
    ("@DeleteProvider", [6031]),
    # SqlSession direct API
    ("SqlSession.select", [6031]),
]
