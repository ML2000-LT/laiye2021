# 综合数据处理工具
## _data_process_tools_

Data process tools based on data labeled by [VGG Image Annotator](https://www.robots.ox.ac.uk/~vgg/software/via/via_demo.html)


- Error Classifier & Json Merger
- Json-Excel Converter
- Repeat Detector
- Key Value Pair Automatic Adder

## Data Conventions
For a command that includes `directory` such as:
```sh
python xxx.py directory
```
This `directory` must follow:
- `.json` and its corresponding folder having the same name
- including only single `.excel` if needed
- the subfolders in `directory` must include only pictures, nothing else
- any subfolders with the name `tmp` might be removed
- tools not using pictures, only the `.json` files needed
- You should get something like:
```
|-- directory
    |-- id_card
        |-- 1.jpg
        |-- 2.jpg
        ...
    |-- id_card.json
    |-- liscence
        |-- liscence1.png
        |-- liscence2.png
        ...
    |-- liscence.json
    ...
```

## Installations


First `cd` into the current `data_process_tools` directory.
To check, type: `pwd` into current terminal and you should get:
```sh
/your/path/data_process_tools
```
Install the dependencies by typing in the following:

```sh
pip install -r requirements.txt
```

Current environment:

```sh
Python 3.8.8
macOS Big Sur 11.3.1
```

## Error Classifier
This tool, specifically the `error_classifier.py` labels each labeled text region with its prediction as attribute `prediction` by the current OCR model and calculated the difference of labeled (artificial) `content` with the predicted `prediction`, and name the difference as `error`. 
It picks out all the `error`$$\neq$$`0` text regions and place it in a new `.json` file with the other text regions in another `.json` file. For example, the original is `liscence.json`, the 2 new files will be `liscence-错误.json`, `liscence-正确.json`. Users can modify in the `xxx-错误.json` directly within the  [VGG Image Annotator](https://www.robots.ox.ac.uk/~vgg/software/via/via_demo.html) tool, save the corresponding `.json` file and merge it with the previous `xxx-正确.json` using the tool `json_merger.py`. 

### Preparations
- Create a folder with all the above convention
- Use either `pwd` to get its absolute `path`

### Usage
`cd` into `data_process_tools/error_classifier.py`, type
```sh
python error_classifier.py /your/absolute/path
```
### Results
For each `.json` file, there will be 2 corresponding files each indicating the regions of which 
1. The labeled content is different from the predicted content with a difference of `error`
2. The labeled content is identical to the predicted content, `error`=`0`
> error = edit_distance(prediction, label) $$\div$$ len(label) 

It would also create a `log.txt`, telling you how long each step took.

### Merging the Error and Correct jsons
Place the manually corrected `xxx-错误.json` with its corresponding `xxx-正确.json` in the same folder, nothing else. 
It should be like  :
```
|-- your/absolute/path
    |-- xxx-错误.json
    |-- xxx-正确.json
```
Now, `cd` into the same `error_classifier.py` directory, type:
```sh
python json_merger.py /your/absolute/path
```
Now you'll get your merged `.json` file.

## Json-Excel Converter
This tool is to convert a `.json` file to an `.xlsx` file with all its text regions, enabling us to handle the data in excel in a mass scale. Also, it can convert the contents within `.xlsx` back, since we only need the final result in `.json` files.
> Future modifications can include cropping the image into the `.xlsx` file to swiftly see if the cropped text region is valid, viz, havig a good boundary and wether the label is correct

The headers in the `.xlsx` file includes json name, image name, region content, region type, region `k-v` pair, image angle, text angle, etc.

### Preparation
See same section of above tool.

### Usage
First `cd` into `/data_process_tools/json-excels`
1. `json` converting to `xlsx`:
```sh
python json2excel.py your/json/path your/excel/path
```
> Second argument optional

2. `xlsx` converting to `json`:
```sh
python excel2json.py your/excel/path
```
> Warning: the original `.json`s might be replaced if at original location

## Repeat Detector
It occurs that often the same text region is manually labeled at the same position repetitively, either purposefully or not. To adress this, we can run this tool and the repeated regions will be displayed in a `-log.txt`.

### Preparations
Same section as above tool.

### Usage
First `cd` into `/data_process_tools/repeat_detector`, type:
```sh
python repeat_detector.py /your/jsons/absolute/path
```

### Result
Several `-log.txt` corresponding to its corresponding `.json` file indicating the number, position, content of the repeating regions, as well as which picture they belong to.

## Key Value Pair Automatic Adder
When we pre-label the dataset by models, we want to automatically add the `key` and `value`, supposing they add up a pair. Such as `Name: John Doe`. `Name` would be a key, if told that the content `Name` is a key of type `type_Name` given in an excel of all the `content`-`key` pair. We will pair up these `key` `value` pair if they are 
- adjacent enough
- on the same horizontal height and having similar height
- the content of the left box is given in the dictionary, given as an excel.

### Preparations
Same section as above tool. But include only one `excel` with two columns namely, `content` and `kv` as headers. The meaning of such is described above.

### Usage
First `cd` into `/data_process_tools/kv_adder`, type:
```sh
python kv-adder.py /your/absolute/path
```
Then the corresponding `.jsons` in the folder will be modified, adding the desired `key` `value` pair as attributes.
