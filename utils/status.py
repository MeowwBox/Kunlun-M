#!/usr/bin/env python
# encoding: utf-8
'''
@author: LoRexxar
@contact: lorexxar@gmail.com
@file: status.py
@time: 2021/8/11 15:31
@desc:

'''

SCAN_ID = -1

_scan_id_provider = None


def set_scan_id_provider(callback):
    """注册获取 scan_id 的回调函数，由 web 层在启动时调用"""
    global _scan_id_provider
    _scan_id_provider = callback


def get_scan_id():
    global SCAN_ID

    if SCAN_ID > 0:
        return SCAN_ID
    elif _scan_id_provider is not None:
        SCAN_ID = _scan_id_provider()
    else:
        return -1

    return SCAN_ID
