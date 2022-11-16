import os
import requests
from securedata import securedata

REDDIT = securedata.getItem("reddit")

print(REDDIT['username'])

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
TOKEN = res.json()['access_token']

headers = {**headers, **{'Authorization': f"bearer {TOKEN}"}}

res = requests.get("https://oauth.reddit.com/r/oldschoolcool/hot",
                   headers=headers, timeout=30)

DOWNLOADED_COUNT = 0
for post in res.json()['data']['children']:
    if DOWNLOADED_COUNT > 4:
        break

    if str(post['data']['url']).endswith('jpg'):
        DOWNLOADED_COUNT += 1
        print("Downloading")
        print(post['data']['url'])

        img = requests.get(post['data']['url'], timeout=30).content
        with open(f"./output/{DOWNLOADED_COUNT}.jpg", 'wb') as handler:
            handler.write(img)

# remove old video
os.system("rm output.mp4")
# create video
os.system("ffmpeg -f image2 -r 1/5 -i ./output/%01d.jpg -vcodec mpeg4 -y ./output/video_noaudio.mp4")

# add audio
os.system("ffmpeg -i ./output/video_noaudio.mp4 -i ./assets/beautiful_life.mp3 -map 0:v -map 1:a -c:v copy -shortest output.mp4")
