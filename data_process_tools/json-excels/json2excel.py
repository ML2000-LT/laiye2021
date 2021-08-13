# -*- coding: utf-8 -*-
import sys
import time
import shutil
from utils import *

def add_serial(jfile):
    """
    在json中加入serial这个attribute(如果必要)
    """
    data = jfile.get_data()
    need = data['_via_attributes']['region']
    if 'serial' in need:
        return
    need['serial'] = {'type': 'text', 'description': '顺序序号', 'default_value': '0'}
    jfile.update_data(data)

def check_illegals(jfile, extra):
    """
    提醒使用者excel中有某些条目并不存在于json之中
    """
    legals = list(jfile.get_data()['_via_attributes']['region'])
    illegals = []
    for el in extra:
        if el == 'picture':
            continue
        if el not in legals:
            illegals.append(el)
    if illegals == []:
        return 0
    print("Warning：excel中有在%s中并不存在的attribute，分别为%s" %(jfile.name, str(illegals)))
    return 1

def get_attr(obj, titles, tmp):
    lst = []
    region = obj.obj
    for el in titles:
        if el == 'type':
            if 'type' not in region['region_attributes']:
                lst.append('unknown')
            else:
                dict = region['region_attributes']['type']
                lst.append([t for t in dict if dict[t] is True])
            continue
        if el == 'shape':
            if 'name' not in region['shape_attributes']:
                lst.append('unknown')
            else:
                lst.append(region['shape_attributes']['name'])
            continue
        if el == 'picture':
            lst.append('')
            continue
        if el not in region['region_attributes']:
            lst.append('unknown')
        else:
            lst.append(region['region_attributes'][el])
    return lst

def single_json2excel(jfile, titles, extra, tmp):
    """
    @params:
        jfile: the json file object
        df: dataframe from excel
    @return:
        df: the updated df
    """
    df = pd.DataFrame(columns = titles)
    data = jfile.get_data()
    for img in data['_via_img_metadata']:
        regions = data['_via_img_metadata'][img]['regions']
        for i, region in enumerate(regions):
            region['region_attributes']['serial'] = str(i + 1)
            obj = Region(region)
            coor = obj.get_raw_coor()
            content = obj.get_content()
            reqs = [jfile.name, img, i + 1, content, coor]
            extras = get_attr(obj, extra, tmp)
            row = pd.DataFrame([reqs + extras], columns = titles)
            df = df.append(row, ignore_index = True)
    jfile.update_data(data)
    return df

def json2excel(foldername, excelname = None):
    """
    @params:
        foldername: 需要转化的包含json的文件夹，里面可以有子文件夹，但请不要有名为tmp的子文件夹会被删除
        excelname: 需要存储的excel文件名，请在表头包含好需要的attribute，如k-v
                   如果没有明确excel文件名，则默认为foldername下的唯一xlsx，如果不唯一则报错
    @return:
        excelname: 同param
    """
    direct = Directory(foldername)
    if excelname is None:
        excelname = direct.finder('.xlsx', 1)[0]
    excel = Xlsxfile(excelname)
    df = excel.get_data()
    if df.shape[0] != 0:
        raise Exception('%s应该只有一行表头，不应该有其他任何内容！' %(os.path.basename(excelname)))
    start = time.time()
    requirements = ['json', '文件名', 'serial', 'content', 'coordinates']
    df = df.drop(columns = [enum for enum in requirements if enum in list(df.columns)])
    extra = list(df.columns)
    for i, enum in enumerate(requirements):
        df.insert(i, enum, [])
    jsons = direct.finder('.json')
    tmp = os.path.join(foldername, 'tmp')
    errors = 0
    N = max(int(len(jsons) * 0.2 + 0.5), 1)
    for i, jfilename in enumerate(jsons):
        jfile = Jsonfile(jfilename)
        add_serial(jfile)
        errors += check_illegals(jfile, extra)
        df = df.append(single_json2excel(jfile, list(df.columns), extra, tmp))
        jfile.save_data()
        if i % N == 0:
            print('\t已处理完成%d%%的json, 耗时%.2f秒' % ((i / N) * 20.0, time.time() - start))
    if errors != 0:
        print("总共出现了%d个错误" %(errors))
    excel.update_data(df)
    excel.save_data()
    print("总计耗时%.2f秒" %(time.time() - start))
    return excelname

if __name__ == '__main__':
    if len(sys.argv) == 2:
        name = json2excel(sys.argv[1])
    else:
        name = json2excel(sys.argv[1], sys.argv[2])
    print('数据收集完毕，存储在%s' %(name))
