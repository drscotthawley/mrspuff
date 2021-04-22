# mrspuff
> A library for Deep Learning education. (deep learning <=> having a school at the bottom of the ocean)


![mrspuff image](https://github.com/drscotthawley/mrspuff/blob/master/images/mrspuff_logo.png?raw=1)

## About
`mrspuff` is a collection of teaching tools for deep learning, intended to work well on [Google Colab](https://colab.research.google.com/) and interface with [fast.ai](https://github.com/fastai/fastai).

## Install

`pip install mrspuff`

## How to use

This is still under development, not ready for widespread public use yet. 

If you want to try it,
you may either import individual routines, as in
```python
from mrspuff.viz import image_and_bars
```
 or import the whole package and access its submodules, e.g.:

```python
import mrspuff as msp

p, t = msp.utils.calc_prob()
```
