# -*- coding: utf-8 -*-
import os
import cv2
import json
import base64
import requests
import Levenshtein
import numpy as np
import pandas as pd
from PIL import Image
from shapely.geometry import Polygon
from thean_tools.ocr import min_rect

class Filesys:
    def __init__(self, filename):
        self.name = filename

    def __repr__(self):
        return "<Name: " + str(self.name) + ">"

class Jsonfile(Filesys):
    def __init__(self, filename = "", data = None):
        self.name = filename
        self.data = data
        if filename != "":
            assert filename.endswith('.json')
            self.dir = filename.split('.json')[0]

    def get_data(self):
        """
        @return:
            data: 返回的json object
        """
        if self.data is not None:
            return self.data
        file = open(self.name)
        data = json.load(file)
        self.data = data
        file.close()
        return data

    def save_data(self, dest = None):
        """
        @params:
            dest: destination to save self.data
        """
        assert self.data != None
        if dest is None:
            dest = self.name
        with open(dest, "w") as f:
            json.dump(self.data, f)
        f.close()

    def update_data(self, data):
        self.data = data

    def kv_dict(self):
        if hasattr(self, 'dict'):
            return self.dict
        dic = self.data['_via_attributes']['region']['k-v']['options']
        inv_dic = {v: k for k, v in dic.items()}
        self.dict = inv_dic
        return inv_dic


class Directory(Filesys):
    def finder(self, ftype, count = 0):
        """
        @params:
            ftypr: 需要的文件type，如'.json', '.xlsx'
            count: 需要的type文件数量
                   当count = 0时，代表无所谓数量
        @return:
            lst: 返回type文件的列表
        """
        cnt = 0
        lst = []
        for root, dirs, files in os.walk(self.name):
            for file in files:
                if str(file).endswith(ftype):
                    cnt += 1
                    if cnt > count and count:
                        raise LookupError("目录下出现超过%d个%s文件！" %(count, ftype))
                    lst.append(os.path.join(self.name, file))
            #the below line is crucial, without it os will walk through subdirectories
            break
        if cnt < count:
            raise LookupError("目录下只有%d个%s文件！" %(cnt, ftype))
        return lst


class Xlsxfile(Filesys):
    def __init__(self, filename):
        super().__init__(filename)

    def get_data(self):
        if hasattr(self, 'data'):
            return self.data
        self.data = pd.read_excel(self.name)
        return self.data

    def update_data(self, ndata):
        self.data = ndata

    def save_data(self, target = None, with_index = False):
        assert hasattr(self, 'data') and self.data is not None
        if target is None:
            target = self.name
        self.data.to_excel(target, index = with_index)

class Recognizer:
    def __init__(self, imgs, model = '', with_prob = False, with_pos = False):
        self.imgs = imgs
        self.model = model
        self.with_prob = with_prob
        self.with_pos = with_pos

    def __repr__(self):
        return str(len(imgs))

    def get_image(img):
        b64 = base64.b64encode(open(image_path, "rb").read())
        return str(b64, 'utf-8')

    def call_host(self, images):
        req = {
            "model_name": self.model,
            "jpeg_imgs": [get_image(img) for img in images],
            "with_char_probability": self.with_prob,
            "with_char_positions": self.with_pos
        }
        host = "http://172.17.202.26:80/v3/ocr/text/general/recognition"
        resp = requests.post(host, json.dumps(req))
        if resp.status_code == 200:
            return json.loads(resp.content)
        else:
            raise Exception("服务器返回错误。status_code应为200, 实际为%d" %(resp.status_code))

    def recognize(self):
        """
        @params:
            img: a list of all .jpg pictures needed to be recognized
        @return:
            probs: a list of all prob of each character recognized
            contents: a list of all contents
        """
        N = len(self.imgs)
        resp = []
        for i in range(0, N, 50):
            try:
                respond = self.call_host(self.imgs[i : min(N, i + 50)])
            except:
                raise Exception("在识别%d到%d的图片时服务器返回错误" %(i, min(N, i + 50)))
            resp.extend(respond)
        probs = []
        contents = []
        cut_ups = []
        for enum in resp['items']:
            contents.append(enum['content'])
            if self.with_prob:
                probs.append(enum['probabilities'])
            if self.with_pos:
                cut_ups.append(enum['cut_up'])
        return contents, probs, cut_ups

class String_Comparator:
    def __init__(self, refs, gens, rprobs = None, gprobs = None):
        assert len(refs) == len(gens)
        self.refs = refs
        self.gens = gens
        if rprobs is not None:
            assert gprobs is not None
            assert len(rprobs) == len(gprobs) and len(rprobs) == len(refs)
        self.rprobs = rprobs
        self.gprobs = gprobs

    def levenshtein_error(self):
        errors = []
        for i in range(len(self.refs)):
            lst.append(Levenshtein.distance(self.refs[i], self.gens[i]) / self.refs[i])
        return errors

    def modify_prob(ref, gen, rprob, gprob):
        ops = Levenshtein.editops(gen, ref)
        replace = [op for op in ops if op[0] == 'replace']
        delete = [op for op in ops if op[0] == 'delete' ]
        insert = [op for op in ops if op[0] == 'insert']
        delete.sort(key = lambda x: x[2])
        insert.sort(key = lambda x: x[1])
        for i in range(len(replace)):
            gprob[replace[i][1]]['char'] = rprob[replace[i][2]]['char']
            gprob[replace[i][1]]['probability'] = 1e-10
        for i in range(len(delete)):
            rprob.insert(delete[i][2] + i, {'char': gen[delete[i][1]], 'probability': gprob[delete[i][1]]['probability']})
            gprob[delete[i][1]]['probability'] = 1e-10
        for i in range(len(insert)):
            gprob.insert(insert[i][1] + i, {'char': ref[insert[i][2]], 'probability': 1e-10})
        return rprob, gprob

    def probability_error(self, lossfunc = None):
        lossfuncs = ['cross_entropy', 'kl_divergence', 'j_divergence']
        if lossfunc is None:
            lossfunc = 'j_divergence'
        if lossfunc not in lossfuncs:
            raise Exception('所用函数名称%s不合法' %(lossfunc))
        for i in range(len(self.refs)):
            self.rprobs[i], self.gprobs[i] = modify_prob(refs[i], gens[i], rprobs[i], gprobs[i])
        errors = []
        funct = getattr(String_Comparator, lossfunc)
        for i in range(len(self.refs)):
            errors.append(funct(rprobs[i], gprobs[i]))
        return errors

    #works well but is not symmetric
    def cross_entropy(rprob, gprob):
        ref = [enum['probability'] for enum in rprob]
        gen = [enum['probability'] for enum in gprob]
        N = len(ref)
        return -sum([ref[i] * math.log(gen[i], 2) for i in range(N)]) / N

    #doesn't work since ref, gen are not prob distributions so loss can be positive & negative
    def kl_divergence(rprob, gprob):
        ref = [enum['probability'] for enum in rprob]
        gen = [enum['probability'] for enum in gprob]
        N = len(ref)
        return sum([ref[i] * math.log(ref[i] / gen[i], 2) for i in range(N)]) / N

    #symmetric
    def j_divergence(rprob, gprob):
        ref = [enum['probability'] for enum in rprob]
        gen = [enum['probability'] for enum in gprob]
        N = len(ref)
        return sum([(ref[i] - gen[i]) * math.log(ref[i] / gen[i], 2) for i in range(N)]) / N

class Region:
    def __init__(self, obj = None, img = None):
        self.obj = obj
        self.im = img

    def __repr__(self):
        if hasattr(self, 'coors'):
            return repr(self.coors)
        return repr(self.obj)

    def get_raw_coor(self):
        assert self.obj is not None
        obj = self.obj['shape_attributes']
        if obj['name'] == 'rect':
            coordinates = [[obj['x'], obj['y']], [obj['x'] + obj['width'], obj['y']],
                           [obj['x'] + obj['width'], obj['y'] + obj['height']], [obj['x'], obj['y'] + obj['height']]]
        else:
            coordinates = []
            if 'all_points_x' not in obj or 'all_points_y' not in obj:
                return None
            for i in range(len(obj['all_points_x'])):
                coordinates.append([obj['all_points_x'][i], obj['all_points_y'][i]])
        return coordinates

    def get_coor(self):
        """
        @params
            obj: an object with attribute 'name' with types 'polygon', 'rect', 'polyline'
        @return
            a list of four coordinates such as [1, 1, 2, 1, 2, 2, 1, 2]
        """
        coordinates = self.get_raw_coor()
        if self.obj['shape_attributes']['name'] not in ['rect', 'polygon']:
            coordinates = None
        if coordinates is None:
            return None
        coor = np.array(coordinates)
        rect = cv2.minAreaRect(coor)
        coor = cv2.boxPoints(rect)
        coordinates = []
        for pt in coor:
            for elem in pt:
                coordinates.append(elem)
        try:
            coordinates = min_rect(coordinates, clockwise = True)
        except:
            return None
        self.coors = coordinates
        return coordinates

    def crop_image(self, dest):
        assert self.im is not None
        coo = self.get_coor()
        img = Image.open(self.im)
        img = np.asarray(img)
        pts1 = np.array(coo, dtype=np.float32).reshape((-1, 2))
        new_w = int(np.math.sqrt((coo[0]-coo[2])**2 + (coo[1]-coo[3])**2))
        new_h = int(np.math.sqrt((coo[0]-coo[6])**2 + (coo[1]-coo[7])**2))
        if new_h < 5:
            return None
        pts2 = np.float32([[0, 0], [new_w, 0], [new_w, new_h], [0, new_h]])
        M = cv2.getPerspectiveTransform(pts1, pts2)
        dst = cv2.warpPerspective(img, M, (new_w, new_h))
        img = Image.fromarray(dst)
        img = img.convert('RGB')
        if img is None:
            return None
        img.save(dest)
        return dest

    def near(self, obj, params, eps = 0.1):
        """
        @params:
            params: params[0] 代表左右框之间距离不能超过_*左框宽度
        @return:
            T/F
        """
        assert type(obj) is Region
        assert params is not None
        assert len(params) > 0
        self.bound()
        obj.bound()
        w = self.bounds[2] - self.bounds[0]
        h = self.bounds[3] - self.bounds[1]
        if len(params) == 1:
            param = params[0]
            if self.bounds[1] > obj.bounds[3] + h * eps or self.bounds[3] < obj.bounds[1] - h * eps:
                return False
            if self.bounds[2] > obj.bounds[0] + w * eps or self.bounds[2] < obj.bounds[0] - param * w:
                return False
            return True

    def split(self, ch):
        left = self.split()

    def bound(self):
        """
        self.bounds 0,1,2,3分别代表最左、下、右、上的横、纵、横、纵坐标
        """
        if hasattr(self, 'bounds'):
            return self.bounds
        assert hasattr(self, 'coors') and self.coors is not None
        c = self.coors
        self.bounds = [min(c[0], c[6]), min(c[1], c[3]), max(c[2], c[4]), max(c[5], c[7])]

    def add_content(self, cont):
        self.content = cont

    def cmp_position(self):
        assert hasattr(self, 'coors') and self.coors is not None
        if hasattr(self, 'bounds'):
            return self.bounds[1] * 10000 + self.bounds[0]
        return self.coors[1] * 10000 + self.coors[0]

    def cmp_attr(self, lst):


    def get_content(self):
        if hasattr(self, 'content'):
            return self.content
        self.content = self.obj['region_attributes']['content']
        return self.content
