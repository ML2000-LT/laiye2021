import json
from error_classifier import *

def data_merge(data1, data2):
    for img in data2['_via_img_metadata']:
        regions = data2['_via_img_metadata'][img]['regions']
        for region in regions:
            data1['_via_img_metadata'][img]['regions'].append(region)
    return data1

def json_merger(file_dir):
    """
    @params:
        file_dir: 该文件夹下应该有且仅有两个.json文件，其余非.json文件被忽略
                  这两个.json文件会合并成为另外一个.json文件
                  这两个文件应该只有region不同，其余必须相同！
    @return:
        file_name:合并完成的文件名
    """
    try:
        files = find_json(file_dir, 2)
    except LookupError:
        print("文件夹里面应该有且仅有两个.json文件！")
    data1 = json_object_returner(os.path.join(file_dir, files[0]))
    data2 = json_object_returner(os.path.join(file_dir, files[1]))
    data = data_merge(data1, data2)
    json_name = files[0].split('.json')[0] + "-合并.json"
    with open(os.path.join(file_dir, json_name), "w") as out_file:
        json.dump(data, out_file)
    out_file.close()
    return json_name

if __name__=="__main__":
    file_dir = sys.argv[1]
    print("合并已完成。合并后的文件名为%s" %(json_merger(file_dir)))



