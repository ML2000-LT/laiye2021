# -*- coding: utf-8 -*-
from utils import *
import numpy as np

def change_pair(x, y, kv):
    a = x.obj['region_attributes']
    b = y.obj['region_attributes']
    if 'type' not in a:
        a['type'] = {}
    if 'type' not in b:
        b['type'] = {}
    a['type']['key'] = True
    b['type']['value'] = True
    a['k-v'] = kv
    b['k-v'] = kv

def kv_single(json_obj, dic):
    data = json_obj.get_data()
    kv_dic = json_obj.kv_dict()
    for img in data['_via_img_metadata']:
        rlst = []
        regions = data['_via_img_metadata'][img]['regions']
        for region in regions:
            obj = Region(region)
            if 'content' in region['region_attributes'] and obj.get_coor() is not None:
                obj.add_content(region['region_attributes']['content'])
                obj.bound()
                rlst.append(obj)
        rlst.sort(key = Region.cmp)
        N = len(rlst)
        for i in range(N):
            if rlst[i].content not in dic:
                continue
            obj = rlst[i]
            ans = []
            for j in range(i - 1, -1, -1):
                if rlst[j].bounds[3] <= obj.bounds[1]:
                    break
                if obj.near(rlst[j], [0.3]):
                    ans.append(rlst[j])
            for j in range(i + 1, N):
                if rlst[j].bounds[1] >= obj.bounds[3]:
                    break
                if obj.near(rlst[j], [0.3]):
                    ans.append(rlst[j])
            if len(ans) != 1:
                continue
            change_pair(obj, ans[0], kv_dic[dic[obj.content]])
    return data

def kv_adder(filename):
    direct = Directory(filename)
    jsons = direct.finder(ftype = '.json')
    excel = Xlsxfile(direct.finder('.xlsx', 1)[0])
    dic = {}
    for i in range(len(excel.data['content'])):
        dic[excel.data['content'][i]] = excel.data['KV'][i]
    for json_file in jsons:
        json_obj = Jsonfile(json_file)
        json_obj.get_data()
        for k, v in dic.items():
            if v not in json_obj.kv_dict():
                raise Exception("excel中有KV名称不合法！错误KV名为：%s" %(v))
        ndata = kv_single(json_obj, dic)
        json_obj.update_data(ndata)
        json_obj.save_data(json_file)

if __name__ == '__main__':
    kv_adder(sys.argv[1])
