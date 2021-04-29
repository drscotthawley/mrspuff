# AUTOGENERATED! DO NOT EDIT! File to edit: scrape.ipynb (unless otherwise specified).

__all__ = ['search_images_ddg', 'download_and_save', 'search_and_download', 'img_scrape', 'browse_images',
           'get_thumb_urls', 'exhibit_urls']

# Cell
from fastcore.basics import *
import numpy as np
import re
import requests
import json
import os, io
from PIL import Image, ImageOps
import hashlib
import shutil
import glob
from pathlib import Path
import subprocess
import time
from IPython.display import HTML
import matplotlib.pyplot as plt
from ipywidgets import interact
from .utils import calc_prob
import pandas as pd

# Cell

#modified from fastbook utils, https://github.com/fastai/course20/blob/master/fastbook/__init__.py
#by Jeremy Howard and Sylvain Gugger.  Just removed the .decode() formatting, and replaced L() with list()
def search_images_ddg(key,max_n=200):
    """By Howard & Gugger: Search for 'key' with DuckDuckGo and return a unique urls of 'max_n' images
    (Adopted from https://github.com/deepanprabhu/duckduckgo-images-api)
    """
    url        = 'https://duckduckgo.com/'
    params     = {'q':key}
    res        = requests.post(url,data=params)
    searchObj  = re.search(r'vqd=([\d-]+)\&',res.text)
    if not searchObj: print('Token Parsing Failed !'); return
    requestUrl = url + 'i.js'
    headers    = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'}
    params     = (('l','us-en'),('o','json'),('q',key),('vqd',searchObj.group(1)),('f',',,,'),('p','1'),('v7exp','a'))
    urls       = []
    while True:
        try:
            res  = requests.get(requestUrl,headers=headers,params=params)
            data = json.loads(res.text)
            for obj in data['results']:
                urls.append(obj['image'])
                max_n = max_n - 1
                if max_n < 1: return list(set(urls))     # dedupe
            if 'next' not in data: return list(set(urls))
            requestUrl = url + data['next']
        except:
            pass

# Cell
def download_and_save(folder_path:str, url:str, verbose:bool=True):
    success = False
    try:
        image_content = requests.get(url).content

    except Exception as e:
        print(f"ERROR - Could not download {url} - {e}")

    try:
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file).convert('RGB')
        file_path = os.path.join(folder_path,hashlib.sha1(image_content).hexdigest()[:10] + '.jpg')
        with open(file_path, 'wb') as f:
            image.save(f, "JPEG", quality=85)
        #if verbose:  print(f"SUCCESS - saved {url} - as {file_path}")
        success = True
    except Exception as e:
        print(f"ERROR - Could not save {url} - {e}")
        file_path = ''
    return file_path


def search_and_download(search_term:str, df=None, target_path:str='./images', num_images:int=10, verbose:bool=True):

    target_folder = os.path.join(target_path,'_'.join(search_term.lower().split(' ')))

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    try_urls = search_images_ddg(search_term, max_n=num_images)
    print(f"...got {len(try_urls)} urls for term '{search_term}'")

    if df is None: df = pd.DataFrame(columns = ['file_path', 'label', 'orig_url'])
    for url in try_urls:
        file_path = download_and_save(target_folder, url, verbose=verbose)
        if file_path != '':
            df = df.append({ 'file_path' : file_path, 'label':search_term, 'orig_url' : url}, ignore_index = True)

    if verbose: print(f"{search_term}: Expected {num_images}, succeeded at saving {len(df)}.")
    return df   # return a dataframe storing successully downloaded files and urls they came from


# Cell
def img_scrape(search_terms:list, target_path:str='./.images', num_images:int=10, verbose:bool=True):

     # clear out directory before use
    for category_path in glob.glob(os.path.join(target_path, "*")):
        shutil.rmtree(category_path)

    df = pd.DataFrame(columns = ['file_path', 'label', 'orig_url'])
    for term in search_terms:
        if verbose: print(f"Searching on term '{term}'...")
        #df = pd.concat([df, search_and_download(search_term = term, target_path=target_path, num_images=num_images)], axis=0)
        df = df.append(search_and_download(search_term = term, target_path=target_path, num_images=num_images), ignore_index = True)

    return df # return list of file paths and original urls

# Cell
def browse_images(dataset):
    print("Select the class from the drop-down, and the image by moving the slider with the mouse or the arrow keys.")
    @interact(term=search_terms)
    def _browse_images(term):
        n = len(dataset[term])
        def view_image(i):
            plt.imshow(dataset[term].images[i], cmap=plt.cm.gray_r, interpolation='nearest')
            plt.show()
        interact(view_image, i=(0,n-1))

# Cell

try:
  from google.colab import drive
  IN_COLAB = True
except:
  IN_COLAB = False


def get_thumb_urls(
    images_dir:str="scraped_images",  # directory of full size images, no / on end
    size:tuple=(150,150),             # max dims of thumbnail; see PIL Image.thumbnail()
    verbose:bool=False                # whether to print status messages or not
    ) -> list:
    """
    (Colab only) This will save thumbnails of images and provide 'hosted' urls to them
    """

    if not IN_COLAB:
        print("Sorry, this only works on Colab")
        return None

    drive.mount('/gdrive')
    thumbs_copy_dir = '/gdrive/My Drive/'+ images_dir + "_thumbs"
    shutil.rmtree(thumbs_copy_dir, ignore_errors=True)      # clear out thumbs dir

    # get all the image filenames with full paths
    image_paths = [path for path in Path(images_dir).resolve().rglob('*') if path.suffix.lower() in ['.jpg', '.png']]

    # create the thumbnails and save them to Drive
    thumb_paths = []
    for f in image_paths:
        t = Path(thumbs_copy_dir) / f.parent.name / f.name
        thumb_paths.append(t)
        t.parent.mkdir(parents=True, exist_ok=True)  # create the parent directories before writing files
        with Image.open(f) as im:
            im.thumbnail(size)
            im.save(t)
    print(f"Thumbnails saved to Google Drive in {thumbs_copy_dir}\nWaiting til URLs are ready.")

    # get thumbnail URLs from Drive (might have to wait a bit for them)
    urls = []
    for tp in thumb_paths:
        count, fid = 0, "local-225"  # need a loop in case Drive needs time to generate FileID
        while ('local-' in fid) and (count < 100):
            fid, count = subprocess.getoutput(f"xattr -p 'user.drive.id' '{tp}' "), count+1
            if 'local-' in fid: time.sleep(1)
        url = f'https://drive.google.com/uc?id={fid}'
        urls.append(url)
        if verbose: print(f"url = {url}")
    return urls

# Cell
def exhibit_urls(targ, labels=['cat','dog','horse']):
    """grabs a set of urls, in order of images that match the labels corresponding to targets"""

    dim = targ.max()+1
    url_store = [[] for t in range(dim)]
    for t in range(dim): # for each set of targets, scrape that many urls for the label
        label, n = labels[t], np.sum(targ == t )# count how many of each target there are
        url_store[t] = search_images_ddg(label)
    return [ url_store[targ[t]].pop(0) for t in range(len(targ)) ] # supply a url matching each target