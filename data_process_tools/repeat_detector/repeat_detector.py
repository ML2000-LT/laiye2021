import os
import json
import cv2
from error_classifier import *

def points2Polygon(point_arr):
    a = np.array(point_arr).reshape(4, 2)  # 四边形二维坐标表示
    poly = Polygon(a).convex_hull
    return poly

# 计算两个多边形区域的交
def intersection(poly1, poly2):
    if not poly1.intersects(poly2):  # 如果两四边形不相交
        intersection_area = 0
    else:
        try:
            intersection_area = poly1.intersection(poly2).area  # 相交面积
        except shapely.geos.TopologicalError:
            intersection_area = 0
    return intersection_area

def IoU(coor1, coor2):
    """
    @params:
        coor1, coor2: have to be the form [1, 2, 3, 4, 5, 6, 7, 8], representing the 4 vertices
    """
    po1 = points2Polygon(coor1)
    po2 = points2Polygon(coor2)
    intersect = intersection(po1, po2)
    return intersect / (po1.area + po2.area - intersect)

def detect_repeat(regions):
    N = len(regions)
    cnt = np.zeros(N).tolist()
    coors = []
    repeat = []
    for i in range(N):
        coo = get_coordinates(regions[i]['shape_attributes'])
        if not coo:
            coors.append(None)
            continue
        coors.append(coo)
    for i in range(N):
        if cnt[i] != 0 or coors[i] is None:
            continue
        for j in range(N):
            if j == i or cnt[j] != 0 or coors[j] is None:
                continue
            if IoU(coors[i], coors[j]) > 0.9:
                cnt[i] += 1
                cnt[j] += 1
        if cnt[i] != 0:
            repeat.append([regions[i]['region_attributes']['content'], cnt[i] + 1])
    return repeat

def region_comparator(region):
    obj = region['shape_attributes']
    if obj['name'] == 'rect':
        return obj['x'] << 13 + obj['y']
    if obj['name'] == 'polygon':
        return obj['all_points_x'][0] << 13 + obj['all_points_y'][0]
    return -1

def repeat_single(data, filename):
    f = open(filename.split('.json')[0] + '-log.txt', "w")
    for img in data['_via_img_metadata']:
        regions = data['_via_img_metadata'][img]['regions']
        result = detect_repeat(regions)
        if len(result) < 1:
            continue
        print("在图片%s中共有%d条不同的重复文本框" %(img, len(result)), file = f)
        for r in result:
            r[0] = r[0].replace('\n', '')
            print("\t内容为：%s, 共%d个文本框" %(r[0], r[1]), file = f)

def repeat_detector(file_dir):
    json_files = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if str(file).endswith(".json"):
                json_files.append(file)
        break
    if len(json_files) == 0:
        raise Exception("目录下没有.json文件！")
    cur = time.time()
    for file in json_files:
        filename = os.path.join(file_dir, file)
        print("正在处理文件%s" %(filename))
        data = json_object_returner(filename)
        repeat_single(data, filename)
    print("总计耗时%.2f秒" %(time.time() - cur))

if __name__=="__main__":
    file_dir = sys.argv[1]
    repeat_detector(file_dir)
