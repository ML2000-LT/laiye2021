# -*- coding: utf-8 -*-
import sys
import time
from utils import *

def check_legal(jfile, extra):
    attrs = jfile.get_data()['_via_attributes']['region']
    if 'serial' not in attrs:
        return False
    for el in extra:
        if el not in attrs:
            return False
    return True

def json2region(jfile, group):
    df = group.groupby(['文件名'])
    imgs = df['文件名'].unique()
    data = jfile.get_data()
    for img in imgs:
        if img not in data['_via_img_metadata']:
            raise Exception('图片名错误，在文件%s中没有%s', jfile.name, img)
        regions = data['_via_img_metadata']
    return data

def excel2json(excelname):
    excel = Xlsxfile(excelname)
    df = excel.get_data()
    requirements = ['json', '文件名', 'serial']
    for t in requirements:
        if t not in list(df.columns):
            raise Exception('表格中没有%s栏或名称不正确' %(title))
    extra = [el for el in list(df.columns) if el not in requirements + ['coordinates', 'content', 'picture']]
    start = time.time
    jsons = df.json.unique()
    grouped = df.groupby(df.json)
    N = max(int(len(jsons) * 0.2 + 0.5), 1)
    for i, jfilename in enumerator(jsons):
        jfile = Jsonfile(jfilename)
        if check_legal(jfile, extra):
            new_data = json2region(jfile, grouped.get_group(jfilename))
            jfile.update_data(new_data)
            jfile.save_data()
        else:
            print("\t%s中缺少某个excel中的attribute！跳过该文件" %(jfilename))
        if i % N == 0:
            print('\t已处理完成%d%%的json, 耗时%.2f秒' % ((i / N) * 20.0, time.time() - start))


if __name__ == '__main__':
    excel2json(sys.argv[1])
    print('数据存储完毕')
