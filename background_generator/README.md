# 合成文本背景生成器
## _background_generator_

Background generator based on data labeled by [VGG Image Annotator](https://www.robots.ox.ac.uk/~vgg/software/via/via_demo.html)
![Labeled Image](./readme_img/raw-bg.png)
![Gernerated Background](./readme_img/gen-bg.jpg)


- Label out all the regions that contains text
- Place the picture and the corresponding json(s) in a folder 
- Run the program and get the background(s)!

## Structure
```
|-- background_generator
    |-- code
        |-- mask.py
        |-- utils.py
    |-- data
        |-- background
            |-- 1.jpg
            |-- 2.jpg
            ...
        |-- mask_image
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
    |-- readme_img
        |-- raw_bg.png
        |-- gen_bg.jpg
    |-- README.md
    |-- requirements.txt
```


## Installations


First `cd` into the current `background_generator` directory.
To check, type: `pwd` into current terminal and you should get:
```sh
/your/path/background_generator
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

## Preparations

- `cd` into the `data` folder
- Put all `.json` files and its correponding folder into `mask_image` folder
- You shoud get the following structure
```
|-- mask_image
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
> Note: `.json` and its corresponding folder must have the same name!
> e.g. `idcard.json` with folder named `idcard`

## Usage
`cd` into `background_generator/code`, type
```sh
python mask.py
```
The terminal should display something like:
```sh
开始生成mask
mask生成完成，用时2.87秒
开始生成背景图片
	已生成20%的背景图片，用时1.07秒
	已生成40%的背景图片，用时3.62秒
	已生成60%的背景图片，用时3.28秒
	已生成80%的背景图片，用时4.19秒
	已生成100%的背景图片，用时3.60秒
背景图片生成完毕。总计用时20.71秒
储存在/your/path/background_generator/data/background
```
The results in `./background_generator/data/background`,
named sequentially `1.jpg`, `2.jpg`, etc.







