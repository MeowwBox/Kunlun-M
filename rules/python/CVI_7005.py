# -*- coding: utf-8 -*-
from utils.api import *


class CVI_7005():
    """
    Python 文件操作 / 路径遍历
    覆盖: open, shutil, os.path, pathlib, Django FileResponse/send_file 等
    """
    def __init__(self):
        self.svid = 7005
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "文件操作"
        self.description = "使用了可能存在路径遍历或文件操作风险的函数"
        self.level = 6
        self.status = True
        self.match_mode = "function-param-regex"
        self.match = r"open\(|os\.path\.join|shutil\.copy|shutil\.copyfile|shutil\.move|os\.remove|os\.unlink|os\.rename|send_file|FileResponse|pathlib\.Path|os\.mkdir|os\.makedirs|shutil\.rmtree|shutil\.make_archive|shutil\.unpack_archive|tempfile\.mktemp"
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = ["open", "join", "copy", "copyfile", "move", "remove", "unlink", "rename", "send_file", "FileResponse", "rmtree", "make_archive", "unpack_archive", "mktemp"]

    def main(self, regex_string):
        """
        二次筛选：过滤纯硬编码路径

        安全模式 (return False):
        - open('/etc/hosts')  硬编码路径
        - open('config.ini')  硬编码文件名
        - shutil.copy('a.txt', 'b.txt')  硬编码

        危险模式 (return None):
        - open('/var/data/' + filename)  变量拼接
        - open(user_input)  变量
        - send_file(filepath)  变量
        """
        if not regex_string:
            return None

        # 检查 open() 的参数
        open_match = re.search(r'\bopen\s*\(\s*(.+)', regex_string, re.I)
        if open_match:
            arg = open_match.group(1).strip()
            # 纯字符串字面量（硬编码路径）
            if re.match(r'^[\'\"][^\'\"]*[\'\"]\s*(?:,|\))', arg):
                return False

        return None
