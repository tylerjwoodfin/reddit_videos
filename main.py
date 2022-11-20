"""
reddit_videos

see README for important information
"""

import os
import math
import textwrap
import requests
from securedata import securedata
from PIL import Image, ImageDraw, ImageFont

IMG_SIZE = (1920, 1080)
IMG_MSG = "This is sample text"
IMG_FONT = ImageFont.truetype('arial.ttf', 60)
REDDIT = securedata.getItem("reddit")


def create_text_image(size, bg_color, message, font, font_color):
    """
    create a title slide between images
    """
    text_image = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(text_image)

    margin = 400
    offset = 500
    for line in textwrap.wrap(message, width=40, break_long_words=False):
        draw.text((margin, offset), line, font=font, fill=font_color)
        offset += font.getsize(line)[1]

    return text_image


def get_scaled_image_size(width, height):
    """
    Resize image to fit in 1920x1080 canvas
    """

    new_width = 0
    new_height = 0

    if min(width, height) == width:
        new_height = 1080
        new_width = (1080/height)*width
    else:
        new_width = 1920
        new_height = (1920/width)*height

    return (round(new_width), round(new_height))


def resize_canvas(old_image_path="314.jpg", new_image_path="save.jpg",
                  canvas_width=500, canvas_height=500):
    """
    Place one image on another image.

    Resize the canvas of old_image_path and store the new image in
    new_image_path. Center the image on the new canvas.
    """
    old_image = Image.open(old_image_path)
    old_width, old_height = old_image.size

    # resize image
    old_image = old_image.resize(
        get_scaled_image_size(old_width, old_height), Image.ANTIALIAS)
    old_width, old_height = old_image.size

    # center the image
    coord_x1 = int(math.floor((canvas_width - old_width) / 2))
    coord_y1 = int(math.floor((canvas_height - old_height) / 2))

    mode = old_image.mode
    if len(mode) == 1:  # L, 1
        new_background = (255)
    if len(mode) == 3:  # RGB
        new_background = (255, 255, 255)
    if len(mode) == 4:  # RGBA, CMYK
        new_background = (255, 255, 255, 255)

    new_image = Image.new(mode, (canvas_width, canvas_height), new_background)
    new_image.paste(old_image, (coord_x1, coord_y1,
                    coord_x1 + old_width, coord_y1 + old_height))
    new_image.save(new_image_path)


def create_video():
    """
    Creates a video from downloaded Reddit files, then adds audio
    """
    auth = requests.auth.HTTPBasicAuth(
        REDDIT['personal_script'], REDDIT['secret'])
    data = {'grant_type': 'password',
            'username': REDDIT['username'],
            'password': REDDIT['password']}

    headers = {'User-Agent': 'MyBot/0.0.1'}

    # send our request for an OAuth token
    res = requests.post('https://www.reddit.com/api/v1/access_token',
                        auth=auth, data=data, headers=headers, timeout=30)

    print("res", res)
    token = res.json()['access_token']

    headers = {**headers, **{'Authorization': f"bearer {token}"}}

    res = requests.get("https://oauth.reddit.com/r/oldschoolcool/hot",
                       headers=headers, timeout=30)

    img_count = 0

    # create title image for beginning of video
    image = create_text_image((1920, 1080), 'yellow',
                              "Old School Cool!", IMG_FONT, 'black')
    image.save("./output/0.jpg", "JPEG")

    # create title image for end of video
    image = create_text_image((1920, 1080), 'yellow',
                              "Thanks for watching. Please like and subscribe!", IMG_FONT, 'black')
    image.save("./output/11.jpg", "JPEG")

    for post in res.json()['data']['children']:
        if img_count > 8:
            break

        if str(post['data']['url']).endswith('jpg'):
            img_count += 1

            # create title card image
            image = create_text_image((1920, 1080), 'black',
                                      post['data']['title'], IMG_FONT, 'yellow')
            image.save(f"./output/{img_count}.jpg", "JPEG")
            img_count += 1

            # save Reddit image
            print(f"Downloading {img_count}")
            print(post['data']['url'])

            img = requests.get(post['data']['url'], timeout=30).content

            with open(f"./output/{img_count}.jpg", 'wb') as handler:
                handler.write(img)

            resize_canvas(f"./output/{img_count}.jpg",
                          f"./output/{img_count}.jpg", 1920, 1080)

    # remove old video
    os.system("rm output.mp4")

    # create video
    os.system(
        "ffmpeg -f image2 -r 1/5 -i ./output/%01d.jpg -vcodec mpeg4 -y ./output/noaudio.mp4")

    # add audio
    os.system("""ffmpeg -i ./output/noaudio.mp4 -i ./assets/beautiful_life.mp3 -map 0:v -map 1:a -c:v copy -shortest output.mp4""")


def main():
    """
    The main entrypoint
    """
    create_video()


main()
