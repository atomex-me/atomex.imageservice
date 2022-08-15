import os
import requests
import io
import uuid

from flask import Flask, send_file
from PIL import Image
from moviepy.video.io.VideoFileClip import VideoFileClip

app = Flask(__name__)

settings = dict(OUTER_IMAGE_FORMAT='png', NFT_PREVIEW_SIZE=(500, 500), TOKEN_PREVIEW_SIZE=(150, 150), TIMEOUT_SEC=240)


@app.route('/<contract>/<token_id>')
def main(contract, token_id):
    try:
        token_id = token_id.split('.')[0]
        tzkt_response = requests.get(f'https://api.tzkt.io/v1/tokens?tokenId={token_id}&contract={contract}')
        if tzkt_response.status_code != 200:
            print(f'TzKT response not 200 on {contract}/{token_id}\n{tzkt_response.text}')
            return tzkt_response.text, tzkt_response.status_code

        json_response = tzkt_response.json()[0]
        artifact_uri = None
        decimals = None

        try:
            decimals = int(json_response["metadata"]["decimals"])

            artifact_uri = json_response["metadata"]["artifactUri"]
            display_uri = json_response["metadata"]["displayUri"]
            if display_uri:
                artifact_uri = display_uri
        except KeyError:
            pass

        ipfs_prefix = 'ipfs://'
        ipfs_http = 'https://ipfs.io/ipfs'

        # handle NFT's preview url
        if (decimals is None or decimals == 0) and artifact_uri is not None:
            size = settings["NFT_PREVIEW_SIZE"]
            if artifact_uri.startswith(ipfs_prefix):
                artifact_uri = f'{ipfs_http}/{artifact_uri[len(ipfs_prefix):]}'

            temp_dir = 'temp'
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            artifact_file_response = requests.get(artifact_uri, timeout=settings["TIMEOUT_SEC"])

        # handle Tokens preview url
        else:
            size = settings["TOKEN_PREVIEW_SIZE"]
            thumbnail_uri = None

            try:
                thumbnail_uri = json_response["metadata"]["thumbnailUri"]
            except KeyError:
                pass
            try:
                thumbnail_uri = json_response["metadata"]["icon"]
            except KeyError:
                pass

            if thumbnail_uri is not None:
                if thumbnail_uri.startswith(ipfs_prefix):
                    thumbnail_uri = f'{ipfs_http}/{thumbnail_uri[len(ipfs_prefix):]}'
                artifact_file_response = requests.get(thumbnail_uri, timeout=settings["TIMEOUT_SEC"])
            else:
                artifact_file_response = requests.get(f'https://services.tzkt.io/v1/avatars/{contract}')

        if artifact_file_response.status_code != 200:
            print(f'Error downloading {artifact_file_response.url}\n{artifact_file_response.text}')
            return f'Token image download error {artifact_file_response.url}', artifact_file_response.status_code

        content_type = artifact_file_response.headers.get('content-type')
        file_dir = f'static/{contract}'
        image_file_name = f'{file_dir}/{token_id}.{settings["OUTER_IMAGE_FORMAT"]}'

        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        if 'image' in content_type.lower():
            img = Image.open(io.BytesIO(artifact_file_response.content))
            img_thumb = crop_max_square(img)
            img_thumb.thumbnail(size)
            img_thumb.save(image_file_name)

            return send_file(image_file_name, f'image/{settings["OUTER_IMAGE_FORMAT"]}')

        if 'video' in content_type.lower():
            temp_video_file_name = f'{temp_dir}/{uuid.uuid4()}.{content_type.split("/")[1]}'
            temp_image_file_name = f'{temp_dir}/{uuid.uuid4()}.{settings["OUTER_IMAGE_FORMAT"]}'

            with open(temp_video_file_name, "wb") as f:
                f.write(artifact_file_response.content)

            generate_video_thumbnail(temp_video_file_name, temp_image_file_name)

            img = Image.open(temp_image_file_name)
            img_thumb = crop_max_square(img)
            img_thumb.thumbnail(size)
            img_thumb.save(image_file_name)

            os.remove(temp_video_file_name)
            os.remove(temp_image_file_name)

    except Exception as e:
        print(f'Exception during getting {contract}/{token_id}\n{e}')
        return send_file('default.png', f'image/{settings["OUTER_IMAGE_FORMAT"]}')


def generate_video_thumbnail(video_file_name, img_file):
    clip = VideoFileClip(video_file_name)
    clip.save_frame(img_file, t=1)
    clip.close()


def crop_max_square(pil_img):
    return crop_center(pil_img, min(pil_img.size), min(pil_img.size))


def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))


if __name__ == '__main__':
    app.run()
