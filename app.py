import os

import requests
import io
from flask import Flask, send_file
from PIL import Image
# from urllib.request import urlopen

app = Flask(__name__)


@app.route('/<contract>/<token_id>')
def main(contract, token_id):
    token_id = token_id.split('.')[0]
    tzkt_response = requests.get(f'https://api.tzkt.io/v1/tokens?tokenId={token_id}&contract={contract}')
    if tzkt_response.status_code != 200:
        return tzkt_response.text, tzkt_response.status_code

    json_response = tzkt_response.json()[0]

    try:
        artifact_uri = json_response["metadata"]["artifactUri"]
        display_uri = json_response["metadata"]["displayUri"]
        if display_uri:
            artifact_uri = display_uri
    except KeyError:
        pass

    ipfs_prefix = "ipfs://"
    if artifact_uri.startswith(ipfs_prefix):
        artifact_uri = f'https://ipfs.io/ipfs/{artifact_uri[len(ipfs_prefix):]}'

    artifact_file_response = requests.get(artifact_uri)

    if artifact_file_response.status_code != 200:
        return 'Ipfs download error', 400

    content_type = artifact_file_response.headers.get('content-type')

    if 'image' in content_type.lower():
        img = Image.open(io.BytesIO(artifact_file_response.content))

        file_object = io.BytesIO()

        size = 500, 500
        img.thumbnail(size)
        mime_type = Image.MIME[img.format]

        img.save(file_object, img.format)
        file_object.seek(0)

        file_dir = f'static/{contract}'

        if not os.path.exists(file_dir):
            os.makedirs(file_dir)

        img.save(f'{file_dir}/{token_id}.png')
        return send_file(file_object, 'image/png')


if __name__ == '__main__':
    app.run()
