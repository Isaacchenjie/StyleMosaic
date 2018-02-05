import os
import argparse
import time
import math
import sys
from multiprocessing import Pool
from PIL import Image, ImageOps
from colorsys import rgb_to_hsv

SLICE_SIZE = 85
OUT_SIZE = 5000
RAW_IMAGE_DIR = 'raw image/'
PROCESSED_IMAGE_DIR = 'processed/'
RESULT_IMAGE_NAME = 'output.jpg'
BLEND_IMAGE_NAME = 'blend_output.jpg'
BLEND_FACTOR = 0.5
REPEAT = 0


def get_avg_hsv_color(img):
    width, height = img.size
    pixels = img.load()
    if type(pixels) is not int:
        data = []
        for x in range(width):
            for y in range(height):
                data.append(pixels[x, y])

        h, s, v = 0, 0, 0
        count = 0
        for x in range(len(data)):
            r = data[x][0]
            g = data[x][1]
            b = data[x][2]
            count += 1

            hsv = rgb_to_hsv(r / 255, g / 255, b / 255)
            h += hsv[0]
            s += hsv[1]
            v += hsv[2]

        h_avg = round(h / count, 3)
        s_avg = round(s / count, 3)
        v_avg = round(v / count, 3)

        if count > 0:
            return h_avg, s_avg, v_avg
        else:
            print('读取图片数据失败')
    else:
        print('PIL读取图片数据失败,请更换图片。')


def find_closest(color, list_colors):
    diff = 1000
    cur_closer = False
    for cur_color in list_colors:
        n_diff = math.sqrt(math.pow(math.fabs(color[0] - cur_color[0]), 2) +
                           math.pow(math.fabs(color[1] - cur_color[1]), 2) +
                           math.pow(math.fabs(color[2] - cur_color[2]), 2))

        if n_diff < diff and cur_color[3] <= REPEAT:
            diff = n_diff
            cur_closer = cur_color
    if not cur_closer:
        print('没有足够的近似图片，建议设置重复')
    cur_closer[3] += 1

    return '({}, {}, {})'.format(cur_closer[0], cur_closer[1], cur_closer[2])


def make_puzzle(img, color_list):
    width, height = img.size
    print('Width = {}, Height = {}'.format(width, height))
    background = Image.new('RGB', img.size, (255, 255, 255))
    total_images = math.floor((width * height) / (SLICE_SIZE * SLICE_SIZE))
    image_count = 0
    for y1 in range(0, height, SLICE_SIZE):
        for x1 in range(0, width, SLICE_SIZE):
            y2 = y1 + SLICE_SIZE
            x2 = x1 + SLICE_SIZE
            new_img = img.crop((x1, y1, x2, y2))
            color = get_avg_hsv_color(new_img)
            closest_img_name = PROCESSED_IMAGE_DIR + str(find_closest(color, color_list)) + '.jpg'
            paste_img = Image.open(closest_img_name)
            image_count += 1
            now_done = math.floor((image_count / total_images) * 100)
            r = '\r[{}{}]{}%'.format('#' * int(now_done), ' ' * int(100 - now_done), now_done)
            sys.stdout.write(r)
            sys.stdout.flush()
            background.paste(paste_img, (x1, y1))

    return background


def get_image_paths():
    paths = []
    for image_name in os.listdir(RAW_IMAGE_DIR):
        paths.append(RAW_IMAGE_DIR + image_name)
    if len(paths) > 0:
        print('一共找到了{}张图片'.format(len(paths)))
    else:
        print('未找到任何图片')

    return paths


def resize_image(in_name, size):
    img = Image.open(in_name)
    img = ImageOps.fit(img, (size, size), Image.ANTIALIAS)

    return img


def convert_image(path):
    img = resize_image(path, SLICE_SIZE)
    color = get_avg_hsv_color(img)
    img.save(str(PROCESSED_IMAGE_DIR) + str(color) + '.jpg')


def convert_all_images():
    paths = get_image_paths()
    print('正在生成马赛克块...')
    pool = Pool()
    pool.map(convert_image, paths)
    pool.close()
    pool.join()


def get_color_list():
    color_list = []
    for image_name in os.listdir(PROCESSED_IMAGE_DIR):
        if image_name != 'None.jpg':
            image_name = image_name.split('.jpg')[0]
            image_name = image_name[1:-1].split(',')
            image_name = list(map(float, image_name))
            image_name.append(0)
            print(image_name)
            color_list.append(image_name)
    return color_list


if __name__ == '__main__':
    parse = argparse.ArgumentParser()
    parse.add_argument('-i', '--input', required=True, help='input image')
    parse.add_argument('-ri', "--rawImageDir", type=str, required=True, help='raw image dir')
    parse.add_argument('-p', '--processedImageDir', type=str, required=True, help='processed image dir')
    parse.add_argument('-o', '--output', type=str, required=False, help='output image')
    parse.add_argument('-e', '--exist', type=str, required=False, help='processed images already exist')
    parse.add_argument('-is', '--inputSize', type=str, required=False, help='mosaic image size')
    parse.add_argument('-os', '--outputSize', type=str, required=False, help='output image size')
    parse.add_argument('-r', '--repeat', type=int, required=False, help='repeat number')
    parse.add_argument('-f', '--blendFactor', type=float, required=False, help='blend factor, range from 0 to 1')
    start_time = time.time()
    args = parse.parse_args()

    image = args.input
    RAW_IMAGE_DIR = args.rawImageDir
    PROCESSED_IMAGE_DIR = args.processedImageDir
    if args.output:
        RESULT_IMAGE_NAME = args.output
        BLEND_IMAGE_NAME = 'blend_' + RESULT_IMAGE_NAME
    if args.inputSize:
        SLICE_SIZE = args.inputSize
    if args.outputSize:
        OUT_SIZE = args.outputSize
    if not args.exist:
        convert_all_images()
    if args.repeat:
        REPEAT = args.repeat
    if args.blendFactor and 0 < args.blendFactor < 1:
        BLEND_FACTOR = args.blendFactor

    img = resize_image(image, OUT_SIZE)
    color_list = get_color_list()
    out = make_puzzle(img, color_list)
    img = Image.blend(out, img, BLEND_FACTOR)
    out.save(RESULT_IMAGE_NAME)
    img.save(BLEND_IMAGE_NAME)

    print('\n已完成, 耗时: {}'.format(time.time() - start_time))
    print('中间结果保存为{}'.format(RESULT_IMAGE_NAME))
    print('最终结果保存为{}'.format(BLEND_IMAGE_NAME))