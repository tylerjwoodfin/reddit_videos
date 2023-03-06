"""
reddit_videos

see README for important information
"""

#!/usr/bin/python

import os
import math
import textwrap
import http.client as httplib
import random
import sys
import time
import requests
import httplib2
from cabinet import cabinet, mail
from PIL import Image, ImageDraw, ImageFont
from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


IMG_SIZE = (1920, 1080)
IMG_MSG = "This is sample text"
IMG_FONT = ImageFont.truetype("freefont/FreeMono.ttf", 60)
REDDIT = cabinet.get("reddit")


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

    os.system("mkdir -p output")

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

            video_title = post['data']['title']

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
    os.system("rm -f output.mp4")

    # create video
    cabinet.log("Creating Video")
    os.system(
        "ffmpeg -f image2 -r 1/5 -i ./output/%01d.jpg -vcodec mpeg4 -y ./output/noaudio.mp4")

    # add audio
    path_reddit_videos = cabinet.get("path", "reddit_videos") or '.'
    path_noaudio = f"{path_reddit_videos}/output/noaudio.mp4"
    path_beautiful_life = f"{path_reddit_videos}/assets/beautiful_life.mp3"
    cmd_video_params = "-map 0:v -map 1:a -c:v copy -shortest output.mp4"
    cmd_video = f"""ffmpeg -i {path_noaudio} -i {path_beautiful_life} {cmd_video_params}"""
    os.system(cmd_video)

    return video_title


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
                        httplib.IncompleteRead, httplib.ImproperConnectionState,
                        httplib.CannotSendRequest, httplib.CannotSendHeader,
                        httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS variable specifies the data in cabinet that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google API Console at
# https://console.cloud.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the cabinet's settings.json -> reddit -> google-oath as follows:

"google-oath": {
            "web": {
                "client_id": "<<your ID here>>",
                "client_secret": "<<your secret here>>",
                "redirect_uris": [],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token"
            }
        }

For more information about the client_secrets file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
"""

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def get_authenticated_service(args):
    """
    Authorize client
    """

    path_reddit_videos = cabinet.get('path', 'reddit_videos')
    if path_reddit_videos:
        path_reddit_videos_f = f"{path_reddit_videos}/"
    else:
        path_reddit_videos_f = ""

    flow = flow_from_clientsecrets(f"{path_reddit_videos_f}client-secrets.json",
                                   scope=YOUTUBE_UPLOAD_SCOPE,
                                   message=MISSING_CLIENT_SECRETS_MESSAGE)

    storage = Storage(f"{sys.argv[0]}-oauth2.json")
    credentials = storage.get()

    cabinet.log("Authorizing Video Upload")
    if credentials is None or credentials.invalid:
        cabinet.log("Could Not Authorize; sending email", level="error")
        mail.send("Re-authorize YouTube", "Hi Tyler,<br>Connect to your cloud server to re-authorize YouTube.")
        credentials = run_flow(flow, storage, args)

    cabinet.log("Returning from authorization flow")
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                 http=credentials.authorize(httplib2.Http()))


def initialize_upload(youtube, options):
    """
    Initialize video upload
    """
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=options.category
        ),
        status=dict(
            privacyStatus=options.privacyStatus
        )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting "chunksize" equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )

    resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.


def resumable_upload(insert_request):
    """
    Upload video
    """
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print("Uploading file...")
            response = insert_request.next_chunk()
            if response is not None:
                if 'snippet' in response[1]:
                    mail.send(
                        "Video Uploaded", "Your video is <a href='https://www.youtube.com/channel/UC2k4-eRjuKbpX2WGjFWa-2A'> now live</a>.")
        except HttpError as http_error:
            if http_error.resp.status in RETRIABLE_STATUS_CODES:
                error = f"A retriable HTTP error {http_error.resp.status} occurred:\n{http_error.content}" % (
                    http_error.resp.status)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as error:
            error = f"A retriable error occurred: {error}"

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                sys.exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print(f"Sleeping {sleep_seconds} seconds and then retrying...")
            time.sleep(sleep_seconds)


def main():
    """
    The main entrypoint
    """
    
    video_title = create_video() or "Old School Cool"

    if len(video_title) > 80:
        video_title = "Old School Cool, Daily Upload"

    argparser.add_argument("--file", default="output.mp4",
                           help="Video file to upload")
    argparser.add_argument("--title", help="Video title", default=video_title)
    argparser.add_argument("--description", help="Video description",
                           default="I found these cool pictures on Reddit and wanted to share them with you all! Make sure to like and subscribe for the latest updates.")
    argparser.add_argument("--category", default="22",
                           help="Numeric video category. " +
                           "See https://techpostplus.com/youtube-video-categories-list-faqs-and-solutions/")
    argparser.add_argument("--keywords", help="Video keywords, comma separated",
                           default="reddit, oldschoolcool, nostalgia")
    argparser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
                           default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
    args = argparser.parse_args()

    if not os.path.exists(args.file):
        sys.exit("Please specify a valid file using the --file= parameter.")

    youtube = get_authenticated_service(args)

    try:
        cabinet.log(f"Uploading video as '{video_title}'")
        initialize_upload(youtube, args)
    except HttpError as error:
        if error.resp.status == 400:
            mail.send("Cannot Upload Video", str(error.content))

        print(f"An HTTP error {error.resp.status} occurred:\n{error.content}")


main()
