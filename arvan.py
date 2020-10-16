import argparse
import base64
import json
import os

import magic
import requests
from dotenv import load_dotenv
from requests.models import PreparedRequest

# TODO add description for arguments
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--channel", required=True)
parser.add_argument("-m", "--mode", required=False)
parser.add_argument("-cm", "--convert_mode", required=False)
parser.add_argument("-g", "--per_page", required=False)
parser.add_argument("-t", "--title", required=False)
parser.add_argument("-f", "--file", required=False)
parser.add_argument("-o", "--out", required=False)
parser.add_argument("-p", "--postfix", required=False)
parser.add_argument("-d", "--dir", required=False)
parser.add_argument("-s", "--second", required=False)
args = parser.parse_args()
load_dotenv()


class UploadVideo:
    def __init__(self, channel, title=0, file_path=0, convert_mode=0, thumb_time=0):
        self.key = os.getenv("key")
        self.channel = channel
        if args.mode == "list":
            return
        self.mode = convert_mode if convert_mode else "auto"
        self.file_name = os.path.basename(file_path)
        self.title = title if title else self.file_name.split(".")[0]
        self.file_path = file_path
        self.thumb_time = thumb_time

        file_name = self.file_name.encode("utf-8")
        base64_bytes = base64.b64encode(file_name)
        self.filename_base64 = base64_bytes.decode("utf-8")
        file_type = str(magic.from_file(self.file_path, mime=True)).encode("ascii")
        base64_bytes = base64.b64encode(file_type)
        self.filetype_base64 = base64_bytes.decode("ascii")
        self.file_size = os.path.getsize(self.file_path)

    def GetChannels(self):
        url = "https://napi.arvancloud.com/vod/2.0/channels"
        res = requests.get(url=url, headers={"Authorization": self.key})

    def GetChannelVideos(self):
        url = f"https://napi.arvancloud.com/vod/2.0/channels/{self.channel}/videos"
        headers = {
            "Authorization": self.key,
        }
        params = {"per_page": args.per_page if args.per_page else 1000}
        req = PreparedRequest()
        req.prepare_url(url, params)
        res = requests.get(req.url, headers=headers)
        print(json.dumps(res.json(), indent=4, sort_keys=True, ensure_ascii=False))
        if args.out:
            with open(args.out, "w+", encoding="utf-8") as out:
                out.write(
                    json.dumps(res.json(), indent=4, sort_keys=True, ensure_ascii=False)
                )

    def GetLink(self):
        url = f"https://napi.arvancloud.com/vod/2.0/channels/{self.channel}/files"
        headers = {
            "Authorization": self.key,
            "tus-resumable": "1.0.0",
            "upload-length": str(self.file_size),
            "upload-metadata": f"filename {self.filename_base64},filetype {self.filetype_base64}",
        }
        res = requests.post(url=url, headers=headers)
        assert res.headers.get("Location") != None
        self.upload_location = res.headers.get("Location")
        return self.upload_location

    def UploadFile(self):
        upload_url = self.GetLink()
        headers = {
            "Authorization": self.key,
            "tus-resumable": "1.0.0",
            "upload-offset": "0",
            "Content-Type": "application/offset+octet-stream",
        }
        with open(self.file_path, "rb") as upload_file:
            print(f"start upload {self.file_path}")
            res = requests.patch(url=upload_url, headers=headers, data=upload_file)
            assert res.status_code == 204

    def CreateVideo(self):
        self.UploadFile()
        url = f"https://napi.arvancloud.com/vod/2.0/channels/{self.channel}/videos"
        headers = {
            "Authorization": self.key,
        }
        data = {
            "title": self.title.encode("utf-8"),
            "file_id": self.upload_location.split("/")[-1],
            "convert_mode": self.mode,
            "parallel_convert": False,
            "thumbnail_time": 1,
        }
        res = requests.post(url=url, headers=headers, json=data)
        if res.status_code == 201:
            print(f"{self.file_name} uploaded\n\n")
        else:
            print(res)


if args.mode == "list":
    up = UploadVideo(args.channel)
    up.GetChannelVideos()
elif args.dir:
    for f in os.listdir(args.dir):
        f = os.path.join("./", args.dir, f)
        if f.endswith(args.postfix):
            print(f)
            up = UploadVideo(
                args.channel, args.title, f, args.convert_mode, args.second
            )
            up.CreateVideo()
else:
    up = UploadVideo(
        args.channel, args.title, args.file, args.convert_mode, args.second
    )
    up.CreateVideo()
