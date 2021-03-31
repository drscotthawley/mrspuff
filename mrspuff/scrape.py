# AUTOGENERATED! DO NOT EDIT! File to edit: 03_scrape.ipynb (unless otherwise specified).

__all__ = ['img_scrape']

# Cell
import os
import time
import requests
import io
from PIL import Image, ImageOps
import hashlib

def img_scrape(search_terms:list, target_path:str='./images', number_images:int=10, verbose:bool=True):

    dataset = {key: Category() for key in search_terms}

    for term in search_terms:
        count, urls = search_and_download(search_term = term, target_path=target_path, number_images=number_images)
        dataset[term].urls = urls   # save urls in case we want them later

    return dataset