# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Yii2'
DEPENDENCIES = {'composer': ['yiisoft/yii2']}


def detect(project_dir, language='php'):
    """检测是否为 Yii2 项目"""
    return (os.path.isfile(os.path.join(project_dir, 'config', 'web.php'))
            and os.path.isdir(os.path.join(project_dir, 'vendor', 'yiisoft')))


FILTER_FUNCTIONS = {
    'Html::encode': {'safe_for': [1000, 10001, 10002]},
    'HtmlPurifier::process': {'safe_for': [1000, 10001, 10002]},
}

CONTROLLED_SOURCES = [
    'Yii::$app->request->get',
    'Yii::$app->request->post',
    'Yii::$app->request->getQueryParam',
    'Yii::$app->request->getBodyParam',
]

EXTRA_SINKS = [
    ("->createCommand(", [1004]),
    ("Yii::\$app->db->createCommand(", [1004]),
]
