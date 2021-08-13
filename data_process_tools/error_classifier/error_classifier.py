import os
import re
import sys
import cv2
import json
import time
import shutil
import base64
import requests
import numpy as np
import Levenshtein
from PIL import Image
from shapely.geometry import Polygon
from thean_tools.ocr import min_rect

def find_json(dir, count = 1):
    """
    @params:
        dir: 文件的目录
        count: 需要的.json文件数量
    @return:
        json_file: 返回.json文件的列表
    """
    cnt = 0
    json_file = []
    for root, dirs, files in os.walk(dir):
        for file in files:
            if str(file).endswith(".json"):
                cnt += 1
                if cnt > count:
                    raise LookupError("目录下出现超过%d个.json文件！" %(count))
                json_file.append(file)
        #the below line is crucial, without it os will walk through subdirectories
        break
    if cnt < count:
        raise LookupError("目录下只有%d个.json文件！" %(cnt))
    return json_file

def json_object_returner(fileName):
    """
    @params
        fileName: a string with absolute path and name ending with .json
                  e.g. /Users/johndoe/Downloads/保险单-15.json
    @return
        a json object
    """
    file = open(fileName)
    data = json.load(file)
    file.close()
    return data

def get_coordinates(obj):
    """
    @params
        obj: an object with attribute 'name' with types 'polygon', 'rect', 'polyline'
    @return
        a list of four coordinates such as [1, 1, 2, 1, 2, 2, 1, 2]
    """
    if obj['name'] == 'rect':
        coordinates = [obj['x'], obj['y'], obj['x'] + obj['width'], obj['y'],                       obj['x'] + obj['width'], obj['y'] + obj['height'], obj['x'], obj['y'] + obj['height']]
    elif obj['name'] == 'polygon':
        coordinates = []
        if len(obj['all_points_x']) != 4:
            for i in range(len(obj['all_points_x'])):
                coordinates.append([obj['all_points_x'][i], obj['all_points_y'][i]])
            coor = np.array(coordinates)
            rect = cv2.minAreaRect(coor)
            coor = cv2.boxPoints(rect)
            coordinates = []
            for pt in coor:
                for elem in pt:
                    coordinates.append(elem)
        else:
            for i in range(len(obj['all_points_x'])):
                coordinates.append(obj['all_points_x'][i])
                coordinates.append(obj['all_points_y'][i])
    else:
        return None
    return coordinates

def crop_image(img, coo, path, region):
    img = np.asarray(img)
    try:
        coo = min_rect(coo, clockwise=True)
    except:
        return None
    pts1 = np.array(coo, dtype=np.float32).reshape((-1, 2))
    new_w = int(np.math.sqrt((coo[0]-coo[2])**2 + (coo[1]-coo[3])**2))
    new_h = int(np.math.sqrt((coo[0]-coo[6])**2 + (coo[1]-coo[7])**2))
    if new_h < 5:
        return None
    pts2 = np.float32([[0, 0], [new_w, 0], [new_w, new_h], [0, new_h]])
    M = cv2.getPerspectiveTransform(pts1, pts2)
    dst = cv2.warpPerspective(img, M, (new_w, new_h))
    img = Image.fromarray(dst)
    angle = region['region_attributes']["textAngle"]
    if angle.isdigit() and int(angle) != 0:
        # 逆时针转动
        img = img.rotate(0 - int(angle))
    return img

def get_image(image_path):
    b64 = base64.b64encode(open(image_path, "rb").read())
    return str(b64, 'utf-8')

def call_recognition(image_paths, model_name):
    req = {
        "model_name":model_name,
        "jpeg_imgs":[get_image(image_path) for image_path in image_paths],
        "with_char_probability":True
    }
    host = "http://172.17.202.26:80/v3/ocr/text/general/recognition"
    resp = requests.post(host, json.dumps(req))
    if resp.status_code == 200:
        return json.loads(resp.content)
    else:
        raise Exception("模型服务器未能返回正确的信息。status_code应为200, 实际为%d" %(resp.status_code))

def recognize(img, model_name = ""):
    """
    @params:
        img: a list of all .jpg pictures needed to be recognized
    @return:
        lst: a list of all contents
    """
    resp = call_recognition(img, model_name)
    lst = []
    if resp is not None:
        for enum in resp["items"]:
            lst.append(enum["content"])
    return lst

def split_filename(sname):
    exts = [".jpg",".jpeg",".png",".PNG",".JPG",".JPEG"]
    for ext in exts:
        if sname.find(ext) > 0:
            return sname.split(ext)[0] + str(ext).lower()
    return sname + '.jpg'

def crop_images(regions, image_path, tmp_dir, cnt, unsupported):
    """
    Crop images from given image and save them in tmp_dir as .jpg
    @params:
        regions: a list of regions
        image_path: the complete path of image needed to crop
        tmp_dir: dir to save the temporary .jpg files
        cnt: the current cnt
    @return:
        cnt: the updated cnt
    """
    img = Image.open(image_path)
    for region in regions:
        region['region_attributes']['error'] = 0
        region['region_attributes']['prediction'] = ''
        # Filter out all unsupported types and empty content regions
        if not region['region_attributes']['content']:
            continue
        if 'tableLine' in region['region_attributes']:
            continue
        if 'type' in region['region_attributes']:
            attr = region['region_attributes']['type']
            if any([(types in attr) for types in unsupported]):
                continue
        coor = get_coordinates(region['shape_attributes'])
        # only detects polygon or rectangular regions
        if not coor:
            continue
        cimg = crop_image(img, coor, image_path, region)
        if cimg is None:
            continue
        cimg = cimg.convert('RGB')
        cnt += 1
        pic_name = str(cnt) + '.jpg'
        save_path = os.path.join(tmp_dir, pic_name)
        cimg.save(save_path)
        region['region_attributes']['error'] = cnt
    return cnt

def update_error(regions, contents):
    reg = re.compile("^[0-9a-zA-Z\W]+$")
    for region in regions:
        if region['region_attributes']['error'] == 0:
            region['region_attributes']['error'] = 'None'
        else:
            label = region['region_attributes']['content']
            pred = contents[region['region_attributes']['error']]
            region['region_attributes']['prediction'] = pred
            #全角全部转成半角
            label = str_q_2_b([label])
            pred = str_q_2_b([pred])
            if not reg.match(label):
                label = label.replace(' ', '')
                pred = pred.replace(' ', '')
            dis = Levenshtein.distance(label, pred)
            region['region_attributes']['error'] = 'None' if dis == 0 else str(dis / len(label))

def str_q_2_b(ustring):
    ss = []
    for s in ustring:
        rstring = ""
        for uchar in s:
            inside_code = ord(uchar)
            if inside_code == 12288:  # 全角空格直接转换
                inside_code = 32
            elif (inside_code >= 65281 and inside_code <= 65374):  # 全角字符（除空格）根据关系转化
                inside_code -= 65248
            rstring += chr(inside_code)
        ss.append(rstring)
    return "".join(ss)

def region_selector(err, non_error, low, high):
    """
    @params:
        non_error: True 代表只返回没有error的region
                   False 代表只返回有error的region，且error范围在(low, high]之间
    @return:
        boolean
    """
    if err == "None":
        return non_error
    if non_error:
        return False
    err = float(err)
    if err > low and err <= high:
        return True
    else:
        return False

def categorize_data(data, non_error = True, low = 0.0, high = 65536.0):
    """
    @params:
        data: data used for cleaning
        non_error: we either want error or not, a boolean value
        low: the lowest error threshold (error > low)
        high: the highest threshold (error <= high)
    @return:
        result: the data table after cleaning
        count: the # of regions that have errors within this threshold, or non error at all
    """
    result = {}
    count = 0
    result['_via_settings'] = data['_via_settings']
    result['_via_attributes'] = data['_via_attributes']
    result['_via_attributes']['region']['error'] = {
        'type': 'text',
        'description': '预测误差',
        'default_value': 'None'
    }
    result['_via_attributes']['region']['prediction'] = {
        'type': 'text',
        'description': '预测值',
        'default_value':''
    }
    result['_via_data_format_version'] = data['_via_data_format_version']
    result['_via_image_id_list'] = data['_via_image_id_list']
    result['_via_img_metadata'] = {}
    for img in data['_via_img_metadata']:
        result['_via_img_metadata'][img] = {}
        regions = data['_via_img_metadata'][img]['regions']
        result['_via_img_metadata'][img]['filename'] = data['_via_img_metadata'][img]['filename']
        result['_via_img_metadata'][img]['size'] = data['_via_img_metadata'][img]['size']
        result['_via_img_metadata'][img]['file_attributes'] = data['_via_img_metadata'][img]['file_attributes']
        result['_via_img_metadata'][img]['regions'] = []
        for region in regions:
            err = region['region_attributes']['error']
            if region_selector(err, non_error, low, high):
                count += 1
                result['_via_img_metadata'][img]['regions'].append(region)
    return result, count

def single_dir_classifier(file_dir, data = None, json_file = None):
    """
    @params:
        file_dir: 需要数据清理的的文件夹的路径，下辖一个.json文件（标注）与所有的该.json所需的.png, .jpeg等文件，不能有二级目录
                  否则二级目录（子文件夹）下所有内容都有可能被删除
    @return：
        ans_dir: 分类完成的2个.json文件所在的文件夹目录（file_dir/categorized）该目录下有2个.json文件，
                 分别代表全部识别正确与识别有错误的文件。更正的操作应在 ～-错误.json中进行之后再调用json_merger
                 以及一个log.txt日志，表示本次测试的各项准确率

    e.g. python error_classifier("foo/bar/")
         >>> "foo/bar/categorized"
    """
    #所有目前不支持的'type'名，如'seal, 'qr_code'等
    unsupported = ['seal', 'qr_code', 'unknown', 'vertical_text', 'table_area', 'image_outline']
    tab = '\t'
    if not data:
        try:
            json_file = find_json(file_dir)[0]
        except LookupError:
            print("目录下应有且仅有一个.json文件！")
        data = json_object_returner(os.path.join(file_dir, json_file))
        tab = ''

    #创建tmp子文件夹，用于临时存储.jpg格式文本框图片，运行后删除
    tmp_dir = os.path.join(file_dir, "tmp")
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.mkdir(tmp_dir)
    cur = time.time()
    cnt = 0
    count = 0
    N = len(data['_via_img_metadata'])
    print(tab + "正在处理来自%d张图片的文本框" %(N))
    N = max(int(N * 0.2 + 0.5), 1)
    for img_name in data['_via_img_metadata']:
        regions = data['_via_img_metadata'][img_name]['regions']
        image_path = os.path.join(file_dir, split_filename(img_name))
        cnt = crop_images(regions, image_path, tmp_dir, cnt, unsupported)
        count += 1
        if count % N == 0:
            print(tab + "\t已完成%d%%的文本框处理" % ((count / N) * 20.0))
    crop_time = time.time()  - cur
    print(tab + "花费%.2f秒处理了%d个文本框" %(crop_time, cnt))
    cur = time.time()
    #send to model and recognise
    tmp_dir = os.path.join(file_dir, "tmp")
    imgs = []
    contents = [""]
    for i in range(1, cnt + 1):
        pic_name = str(i) + '.jpg'
        imgs.append(os.path.join(tmp_dir, pic_name))
        if i % 50 == 0:
            received = recognize(imgs)
            if len(received) != len(imgs):
                raise Exception("有未能成功识别的文本框！")
            contents.extend(received)
            imgs.clear()
            if i % 1000 == 0:
                print(tab + "\t已识别%d个文本框" %(len(contents) - 1))
    if len(imgs):
        contents.extend(recognize(imgs))
        imgs.clear()
    rec_time = time.time() - cur
    print(tab + "花费%.2f秒识别了%d个文本框" %(rec_time, len(contents) - 1))
    shutil.rmtree(tmp_dir)

    for img_name in data['_via_img_metadata']:
        regions = data['_via_img_metadata'][img_name]['regions']
        update_error(regions, contents)
    #创建categorized子文件夹，保存最后答案
    ans_dir = os.path.join(file_dir, "categorized")
    if os.path.isdir(ans_dir):
        shutil.rmtree(ans_dir)
    os.mkdir(ans_dir)
    json_name = json_file.split('.json')[0]
    #只保留预测正确且加入了error, prediction两个attribute的新json文件
    right_data, cnt_right = categorize_data(data)
    with open(os.path.join(ans_dir, json_name + "-正确.json"), "w") as out_file:
        json.dump(right_data, out_file)
    out_file.close()
    #只保留预测错误的region，其他region全部删除
    wrong_data, cnt_wrong = categorize_data(data, non_error = False)
    with open(os.path.join(ans_dir, json_name + "-错误.json"), "w") as out_file:
        json.dump(wrong_data, out_file)
    out_file.close()
    print(tab + "%d个文本框有可能有错误，占%.2f%%" %(cnt_wrong, (cnt_wrong / cnt) * 100))
    with open(os.path.join(ans_dir, "log.txt"), "w") as f:
        print("总计处理了%d张图片" %(len(data['_via_img_metadata'])), file = f)
        print("分割并识别了%d个文本框" %(cnt), file = f)
        print("%d个文本框有可能有错误，占%.2f%%" %(cnt_wrong, (cnt_wrong / cnt) * 100), file = f)
        print("花费了%.2f秒处理文本框" %(crop_time), file = f)
        print("花费了%.2f秒识别图片" %(rec_time), file = f)
    f.close()
    return ans_dir

def error_classifier(file_dir):
    """
    @return:
        directories: a list of directories that contain the categorized info
    """
    cnt = 0
    json_files = []
    directories = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if str(file).endswith(".json"):
                cnt += 1
                json_files.append(file)
        break
    if cnt == 0:
        raise Exception("目录下没有.json文件！")
    cur = time.time()
    for file in json_files:
        sub_dir = os.path.join(file_dir, file.split('.json')[0])
        if not os.path.isdir(sub_dir):
            raise Exception("存在多个.json文件，且不存在其文件名对应的文件夹！")
        data = json_object_returner(os.path.join(file_dir, file))
        print("正在分类文件夹：%s" %(sub_dir))
        directories.append(single_dir_classifier(sub_dir, data, file))
    print("总计耗时%.2f秒" %(time.time() - cur))
    return directories

if __name__=="__main__":
    file_dir = sys.argv[1]
    lst = error_classifier(file_dir)
    print("分类好的文件在如下文件夹：")
    for dirs in lst:
        print('\t' + dirs)
