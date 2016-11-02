# coding=utf-8
# 亿方云Sync反编译脚本，也可以用来反编译其他文件
# 1.python2 ./lib/uncompyle2/setup.py install
# 2.
import os
import commands
OPEN_DIR = "/media/xuning/徐宁"
UNCOM_TYPE = ".pyc"
RES_TYPE = ".py"
SUCCESS_COUNT=1
ERROR_COUNT=0
print "开始进行反编译："
for root, dirs, files in os.walk(OPEN_DIR):
    for index, file in enumerate(files):
        f_n_l = os.path.splitext(file)
        f_a_p=os.path.join(root, file)
        f_p_p=f_a_p.split(str(f_n_l[0]))[0]
        f_n=str(f_n_l[0])
        if f_n_l[1] == UNCOM_TYPE:
            print("开始第"+str(SUCCESS_COUNT)+"个文件...")
            exec_res = commands.getstatusoutput("./uncompyle2 " + f_a_p + " > " + f_p_p+f_n+RES_TYPE)
            if exec_res[1] == '':
                os.remove(f_a_p)
                SUCCESS_COUNT=SUCCESS_COUNT+1
            else:
                ERROR_COUNT=ERROR_COUNT+1
print("共计有"+str(SUCCESS_COUNT-1)+"个文件完成反编译,"+str(ERROR_COUNT)+"个失败")

