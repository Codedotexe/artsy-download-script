#!/usr/bin/env python
from PIL import Image
from io import BytesIO
import argparse
import json
import re
import requests

def extractPaintingData(artsyPageUrl):
	response = requests.get(args.url)
	if not response.status_code == 200:
		raise Exception('Bad response from Artsy, cannot get the page you asked for.')

	htmlRaw = response.content.decode()
	jsonRawMatch = re.search("__RELAY_BOOTSTRAP__\s*=\s*\"(.*)\"", htmlRaw)
	if not jsonRawMatch:
		raise Exception("Could not extract json data from the page")

	jsonRaw = jsonRawMatch.group(1).encode().decode("unicode_escape")
	return json.loads(jsonRaw)[0][1]["json"]["data"]["artwork"]

def assembleImage(tileBaseUrl, imageWidth, imageHeight, tileSize, tilesXCount, tilesYCount, tileFormat):
	# There are various different tileset_ids of different sizes, so we iterate
	# through them to try to find the largest available tilesetID.
	tilesetID = 0
	for _id in range(0, 20):
		tileUrl = f"{tileBaseUrl}/{_id}/{0}_{0}.{tileFormat}"
		response = requests.get(tileUrl)
		# All of the tiles are served via S3, and we get a 404 response when
		# the requeset tile is not available. This usually means that we've passed
		# the largest tileset available, so we can stop looking for larger ones.
		if response.status_code != 200:
			break
		tilesetID = _id

	print('Beginning download...')
	finalImage = Image.new('RGB', (imageWidth, imageHeight))
	for i in range(tilesXCount):
		for j in range(tilesYCount):
			tileUrl = f"{tileBaseUrl}/{tilesetID}/{i}_{j}.{tileFormat}"
			print(f'Downloading tile from {tileUrl}')
			response = requests.get(tileUrl)

			if response.status_code == 200:
				tileImage = Image.open(BytesIO(response.content))
				finalImage.paste(tileImage, (i * tileSize, j * tileSize))
			else:
				print(f"HTTP-Error for {tileUrl}")
	
	return finalImage

def downloadImages(paintingData):
	for imageNum, image in enumerate(paintingData["figures"]):
		tileBaseUrl = image["deepZoom"]["Image"]["Url"].rstrip("/")
		tileFormat = image["deepZoom"]["Image"]["Format"]
		imageWidth = image["deepZoom"]["Image"]["Size"]["Width"]
		imageHeight = image["deepZoom"]["Image"]["Size"]["Height"]
		tileSize = image["deepZoom"]["Image"]["TileSize"]
		tilesXCount = int(imageWidth / tileSize) + 1
		tilesYCount = int(imageHeight / tileSize) + 1
		slug = paintingData["slug"]

		finalImage = assembleImage(tileBaseUrl, imageWidth, imageHeight, tileSize, tilesXCount, tilesYCount, tileFormat)
		filename = f"{slug}-{imageNum}.{tileFormat}"
		finalImage.save(filename)
		print(f'Downloaded to {filename} at {imageWidth}x{imageHeight}')

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("url")
	args = parser.parse_args()

	paintingData = extractPaintingData(args.url)
	downloadImages(paintingData)