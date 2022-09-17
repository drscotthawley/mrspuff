# AUTOGENERATED! DO NOT EDIT! File to edit: scrape.ipynb (unless otherwise specified).

__all__ = ['search_images_ddg', 'download_and_save', 'search_and_download', 'img_scrape', 'browse_images',
           'get_thumb_urls', 'exhibit_urls', 'scrape_for_me', 'download']

# Cell
from fastcore.basics import *
from fastai.vision.all import *
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
from .utils import calc_prob, on_colab
import pandas as pd
import random
import string
import functools
import pathlib
from tqdm.auto import tqdm
from duckduckgo_search import ddg_images

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
    image_paths=None,                 # files we want; "None" = all in images_dir
    images_dir:str="scraped_images",  # directory of full size images, no / on end
    size:tuple=(100,100),             # max dims of thumbnail; see PIL Image.thumbnail()
    verbose:bool=False                # whether to print status messages or not
    ) -> list:
    """
    This will save thumbnails of images and provide 'hosted' urls to them if on Colab
    """

    thumbs_copy_dir = images_dir + "_thumbs"
    if IN_COLAB:
        print("Generating (URLS of) thumbnail images...")
        drive.mount('/gdrive')
        thumbs_copy_dir = '/gdrive/My Drive/'+ thumbs_copy_dir
    shutil.rmtree(thumbs_copy_dir, ignore_errors=True)      # clear out thumbs dir

    # get all the image filenames with full paths
    if image_paths is None:
        image_paths = [path for path in Path(images_dir).resolve().rglob('*') if path.suffix.lower() in ['.jpg', '.png']]

    # create the thumbnails and save them to Drive
    thumb_paths = []
    for fname in image_paths:
        fname = Path(fname) # just as a precaution
        tname = Path(thumbs_copy_dir) / fname.parent.name / fname.name
        tname.parent.mkdir(parents=True, exist_ok=True)  # create the parent directories before writing files
        with Image.open(fname) as im:
            im.thumbnail(size)
            if verbose: print(f"Attempting to save {tname}")
            try:
                im.save(tname)
            except OSError:  # sometimes getting jpg save errors, try those as png
                tname = Path(str(tname) +'.png')
                im.save(tname)
        thumb_paths.append(tname)

    if not IN_COLAB: return [str(t) for t in thumb_paths]  # For local runs, need to un-Path in order to serialize JSON

    print(f"Thumbnails saved to Google Drive in {thumbs_copy_dir}/\nWaiting on Google Drive until URLs are ready.\n")

    # get thumbnail URLs from Drive (might have to wait a bit for them)
    urls = []
    for tp in thumb_paths:
        count, timeout, fid = 0, 60, "local-225"  # need a loop in case Drive needs time to generate FileID
        while ('local-' in fid) and (count < timeout):
            fid, count = subprocess.getoutput(f"xattr -p 'user.drive.id' '{tp}' "), count+1
            if 'local-' in fid: time.sleep(1)      # url still isn't ready; wait a second
        if 'local-' in fid:
            print(f"Error, unable to generate URL for {fid}")
        else:
            urls.append(f'https://drive.google.com/uc?id={fid}')
            if verbose: print(f"url = {urls[-1]}")

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

# Cell

# actually here's a newer interface that I prefer
def scrape_for_me(dl_path, labels, search_suffix, erase_dir=True, max_n=100):
    if erase_dir:
        shutil.rmtree(dl_path, ignore_errors=True)
    path = Path(dl_path)
    if not path.exists(): path.mkdir()
    for o in labels:            # scrape images off the web
        search_term = (f'{o} {search_suffix}').strip()
        dest = (path/o)
        dest.mkdir(exist_ok=True)
        #urls = search_images_ddg(f'{search_term}', max_n=max_n)
        search_results = ddg_images(f'{search_term}', max_results=max_n)  # ddg_images returns a list of dicts
        urls = [d['image'] for d in search_results] # grab values of 'image' field
        urls = [ x for x in urls if ("magpies" not in x) and ("charliebears" not in x) ]   # kludge for now to keep download_images from hanging
        print(f"{search_term}: Got {len(urls)} image URLs. Downloading images...", flush=True)
        print("   urls = ",urls, flush=True)
        download_images(dest, urls=urls, preserve_filename=True)
        print("    Images downloaded." , flush=True)

    print("Doing some more setting up & checking on the downloaded files...")
    fns = get_image_files(path)     # list image filenames
    failed = verify_images(fns)     # check if any are unloadable

    # remove what's unloadable
    failed.map(Path.unlink);
    if failed != []:
        _ = [fns.remove(f) for f in failed]

    #Extra: append a random string before suffix to avoid filename collisions if we change categories later
    fns = get_image_files(path)
    print("Fns = ",fns, flush=True)
    for i, f in enumerate(fns):
        f_no_ext, ext = os.path.splitext(f)[0], f.suffix
        rnd_str = '_'+''.join(random.choice(string.ascii_letters) for i in range(10))
        final = f_no_ext + rnd_str +ext
        shutil.move(f, final)
        fns[i] = Path(final)  # rewrite the filename list entry

    # Extra: To avoid Transparency warnings, convert PNG images to RGBA, from https://forums.fast.ai/t/errors-when-training-the-bear-image-classification-model/83422/9
    #fns = get_image_files(path)
    converted = L()
    for image in fns:
        if '.png' in str(image):
            im = Image.open(image)
            converted.append(image)  # old file name before resaving
            im.convert("RGBA").save(f"{image}2.png")
    converted.map(Path.unlink); # delete originals
    print(f"After checking images for issues, {len(get_image_files(path))} (total) images remain.")
    return path     # and return a pathlib object pointing to image dir

# Cell
def download(url, fname, skip_if_exists=True):
    "downloads a file from URL to local file fname"
    # attribution: cf. https://stackoverflow.com/a/63831344/4259243
    if skip_if_exists and os.path.exists(fname):
        print(f"File {fname} already exists. Returning.")
        return
    resp = requests.get(url, stream=True)
    total = int(resp.headers.get('content-length', 0))
    with open(fname, 'wb') as file, tqdm(
            desc=fname,
            total=total,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
    ) as bar:
        for data in resp.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)