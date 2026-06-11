import os
import sys

# 多层间接调用测试
user_input = sys.argv[1]
func = os.system       # 第一层：赋值
func2 = func            # 第二层：传递
func2(user_input)       # 第三层：间接调用，应检出
