# -*- coding: utf-8 -*-
import time
import shutil
from utils import *
import matplotlib.pyplot as plt
from skimage.draw import polygon
from scipy.spatial import ConvexHull

def get_name(sname):
    exts = [".jpg",".jpeg",".png",".PNG",".JPG",".JPEG"]
    for ext in exts:
        if sname.find(ext) > 0:
            return sname.split(ext)[0] + str(ext).lower()
    return sname + '.jpg'

def mask_json(jfile, img_dir, isave, msave, cnt):
    data = jfile.get_data()
    for img in data['_via_img_metadata']:
        rimg = os.path.join(img_dir, get_name(img))
        if not os.path.isfile(rimg):
            continue
        cnt += 1
        shutil.copyfile(rimg, os.path.join(isave, str(cnt) + '.jpg'))
        image = Image.open(rimg)
        w, h = image.size
        image.close()
        mask = np.zeros((h, w), 'uint8')
        regions = data['_via_img_metadata'][img]['regions']
        for region in regions:
            obj = Region(region)
            coors = obj.get_raw_coor()
            if len(coors) < 1:
                continue
            coors = np.array(coors)
            hull = ConvexHull(coors)
            rs, cs = polygon(coors[hull.vertices, 1], coors[hull.vertices, 0], mask.shape)
            mask[rs, cs] = 255
        mask = Image.fromarray(mask, 'L')
        mask.save(os.path.join(msave, str(cnt) + '.jpg'))
        mask.close()
    return cnt

def get_mask():
    start = time.time()
    cwd = os.path.dirname(os.path.realpath(__file__))
    parent = os.path.abspath(os.path.join(cwd, os.pardir))
    direct_name = os.path.join(parent, 'data/mask_image')
    target = os.path.join(parent, 'data/background')
    img_save = os.path.join(target, 'img')
    mask_save = os.path.join(target, 'mask')
    if os.path.isdir(target):
        shutil.rmtree(target)
    if os.path.isdir(img_save):
        shutil.rmtree(img_save)
    if os.path.isdir(mask_save):
        shutil.rmtree(mask_save)
    os.mkdir(target)
    os.mkdir(img_save)
    os.mkdir(mask_save)
    direct = Directory(direct_name)
    jsons = direct.finder('json')
    cnt = 0
    print('开始生成mask')
    for jname in jsons:
        jfile = Jsonfile(jname)
        img_dir = jname.split('.json')[0]
        cnt = mask_json(jfile, img_dir, img_save, mask_save, cnt)
    print('mask生成完成，用时%.2f秒' %(time.time() - start))
    print('开始生成背景图片')
    N = max(int(cnt * 0.2 + 0.5), 1)
    prev = time.time()
    for i in range(1, cnt + 1):
        iname = str(i) + '.jpg'
        img = cv2.imread(os.path.join(img_save, iname))
        mask = cv2.imread(os.path.join(mask_save, iname), 0)
        dst = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
        cv2.imwrite(os.path.join(target, iname), dst)
        if i % N == 0:
            print('\t已生成%d%%的背景图片，用时%.2f秒' % ((i / N) * 20.0, time.time() - prev))
            prev = time.time()
    shutil.rmtree(img_save)
    shutil.rmtree(mask_save)
    print('背景图片生成完毕。总计用时%.2f秒' %(time.time() - start))
    print('储存在%s' %(target))
    return target

if __name__ == '__main__':
    get_mask()
