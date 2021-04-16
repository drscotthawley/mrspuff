# AUTOGENERATED! DO NOT EDIT! File to edit: viz.ipynb (unless otherwise specified).

__all__ = ['TrianglePlot2D_MPL', 'TrianglePlot3D_Plotly', 'TrianglePlot2D_Bokeh', 'CDH_SAMPLE_URLS', 'VizPreds',
           'image_and_bars', 'sorted_eig', 'pca_proj']

# Cell
import matplotlib.pyplot as plt
import numpy as np
from numpy import linalg as LA
from fastcore.basics import *
from fastai.callback.core import Callback
from fastai.callback.progress import ProgressCallback
from .utils import calc_prob
import plotly.graph_objects as go
from bokeh.plotting import figure, ColumnDataSource, output_file, show
from bokeh.io import output_notebook
from bokeh.models import Label

# Cell
class TrianglePlot2D_MPL():
    "Plot categority predictions for 3 categories - matplotlib style"
    """ pred: (n,3): probability values of n data points in each of 3 classes
        targ: (n):   target value (0,1,2) for each data point"""
    def __init__(self, pred, targ=None, labels=['0','1','2'], show_bounds=True):
        store_attr()
        self.fig = plt.figure(figsize=(5,4))
        self.ax = self.fig.add_subplot(111)
        self.ax.text(-1,0, labels[0], ha='right', va='top', size=12)
        self.ax.text(1,0, labels[1], size=12, va='top')
        self.ax.text(0,1, labels[2], va='bottom', ha='center', size=12)
        if show_bounds: # draw lines for decision boundaries, and 'ideal' points
            self.ax.plot([0,0],[0.333,0], color='black')
            self.ax.plot([0,.5],[0.333,.5], color='black')
            self.ax.plot([0,-.5],[0.333,.5], color='black')
            self.ax.plot(-1,0, marker='o', color='black')
            self.ax.plot(1,0, marker='o', color='black')
            self.ax.plot(0,1, marker='o', color='black')
        eps = 0.02
        self.ax.set_xlim(-1-eps,1+eps)
        self.ax.set_ylim(-eps,1+eps)
        self.ax.set_axis_off()
    def do_plot(self):
        colors = pred if (self.targ is None) else [ ['red','green','blue'][i] for i in self.targ]
        self.scat = self.ax.scatter(self.pred.T[1]-self.pred.T[0],self.pred.T[2], facecolors=colors, marker='o')
        plt.tight_layout()
        return plt
    def update(self,pred,targ):
        self.pred, self.targ = pred, targ
        return self.do_plot()

# Cell
class TrianglePlot3D_Plotly():
    def __init__(self,
        pred,                       # prediction values, probabilities for each class
        targ=None,                  # target values, singly enocde (not one-hot), if none, RGB colors are used
        labels=['x','y','z'],       # class labels
        show_bounds:bool=False,     # show inter-class boundaries or not
        show_labels:bool=True,      # point to class ideal poles with arrows & labels
        show_axes:bool=True,        # show axes or not
        poles_included=False,         # tells whether the "pole" points / triangle tips are already included in the beginning of preds
        cmap='jet'):
        "plot a 3d triangle plot using plot.ly."

        store_attr()


    def do_plot(self):

        if self.targ is None:
            colors, dim = pred, 3
        else:
            colors, dim = [ ['red','green','blue','orange'][i] for i in self.targ], max(self.targ)+1

        poles = self.pred[0:dim,:] if self.poles_included else np.eye(dim)

        fig = go.Figure(data=[go.Scatter3d(x=self.pred[:,0], y=self.pred[:,1], z=self.pred[:,2],
            mode='markers', marker=dict(size=5, opacity=0.6, color=colors))])
        if self.show_labels:
            fig.update_layout(scene = dict(
                xaxis_title=f'{self.labels[0]} - ness', yaxis_title=f'{labels[1]} - ness', zaxis_title=f'{self.labels[2]} - ness',
                # add little arrows pointing to the "poles" or tips
                annotations = [ dict(text=self.labels[i], xanchor='center', x=poles[i,0], y=poles[i,1], z=poles[i,2]) for i in range(dim)]),
                width=700, margin=dict(r=20, b=10, l=10, t=10), showlegend=False
                )

        if self.show_bounds:
            fig.add_trace( go.Scatter3d(mode='lines', x=[0.333,0.5], y=[0.333,0.5], z=[0.333,0],
                line=dict(color='black', width=5) ))
            fig.add_trace( go.Scatter3d(mode='lines', x=[0.333,0], y=[0.333,0.5], z=[0.333,0.5],
                line=dict(color='black', width=5) ))
            fig.add_trace( go.Scatter3d(mode='lines', x=[0.333,0.5], y=[0.333,0], z=[0.333,0.5],
                line=dict(color='black', width=5) ))

        if not self.show_axes:
            fig.update_layout(scene=dict(
                xaxis=dict(showticklabels=False, title=''),
                yaxis=dict(showticklabels=False, title=''),
                zaxis=dict(showticklabels=False, title='')))

        return fig.show()

# Cell

# cat-dog-horse sample image urls (Warning: these may change & stop working; perhaps switch to Imgur)
CDH_SAMPLE_URLS = ['https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Felis_silvestris_catus_lying_on_rice_straw.jpg/220px-Felis_silvestris_catus_lying_on_rice_straw.jpg',
    'https://upload.wikimedia.org/wikipedia/commons/e/e3/Perfect_Side_View_Of_Black_Labrador_North_East_England.JPG',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/SilverMorgan.jpg/250px-SilverMorgan.jpg']


class TrianglePlot2D_Bokeh():
    """This gives a 2d plot with image tooltips when the mouse hovers over a data point."""
    # NOTE: in Markdown cells before trying to show the plot, you may need to
    # force your own JQery import in order for the graph to appear (i.e. if you
    # get "Uncaught ReferenceError: $ is not defined").  If so, add this:
    # <script src="//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js"></script>

    def __init__(self,
            pred,                       # (n,3): probability values of n data points in each of 3 classes
            targ,                       # (n):   target value (0,1,2) for each data point
            labels:list=['0','1','2'],  # the class labels
            show_bounds:bool=False,     # show inter-class boundaries or not
            show_labels:bool=True,      # point to class ideal poles with arrows & labels
            show_axes:bool=True,        # show axes or not
            urls:list=None              # image urls to display upon mouseover (default: stock images)
            ) -> None:                  # __init__ isn't allowed to return anything (it's a Python thing)
        store_attr()
        output_notebook()   # output_file("toolbar.html")
        self.colors = ["blue","red","green"]
        self.TOOLTIPS_HTML = """
            <div>
                <div>
                    <img
                        src="@imgs" height="50" alt="@imgs"
                        style="float: left; margin: 0px 15px 15px 0px;"
                        border="2"
                    ></img>
                </div>
                <div>
                    <span style="font-size: 17px; font-weight: bold;">@desc</span>
                    <span style="font-size: 15px; color: #966;">[$index]</span>
                </div>
                <!---commenting-out coordinate values <div>
                    <span style="font-size: 10px; color: #696;">($x, $y)</span>
                </div> -->
            </div>
        """
        self.clear()
        return

    def clear(self):
        self.p = figure(plot_width=400, plot_height=350, tooltips=self.TOOLTIPS_HTML, title="Mouse over the dots")

    def do_plot(self):
        xs, ys = self.pred.T[1] - self.pred.T[0], self.pred.T[2]

        if self.show_bounds:
            self.p.line([0, 0],[0.333,0], line_width=2, color='black')
            self.p.line([0,.5],[0.333,.5], line_width=2, color='black')
            self.p.line([0,-.5],[0.333,.5], line_width=2, color='black')

        for i in range(self.pred.shape[-1]):  # for each category
            jind = np.where(self.targ == i)
            x, y = xs[jind], ys[jind]
            n = len(y)
            urls = [CDH_SAMPLE_URLS[i]]*n if self.urls is None else self.urls
            source = ColumnDataSource( data=dict(x=x, y=y, desc=[self.labels[i]]*n, imgs=urls ) )
            self.p.circle('x', 'y', size=6, line_color=self.colors[i], fill_color=self.colors[i], source=source)

        if self.show_labels:
            self.p.add_layout( Label(x=-1, y=0, text=self.labels[0], text_align='right'))
            self.p.add_layout( Label(x=1, y=0, text=self.labels[1]))
            self.p.add_layout( Label(x=0, y=1, text=self.labels[2], text_align='center'))



        return self.p

    def update(self, pred, targ):
        self.pred, self.targ = pred, targ
        self.clear()
        return self.do_plot()

# Cell
class VizPreds(Callback):
    "This fastai callback is designed to call the bokeh triangle plot with each batch of training, using validation data."
    order = ProgressCallback.order+1
    def __init__(self,
        method=TrianglePlot2D_Bokeh   # callback to plotting method; must have ".do_plot(preds,targs)"
    ): self.method = method
    def before_fit(self, **kwargs): self.plot = self.method(labels=self.dls.vocab)
    def after_batch(self, **kwargs):
        if not self.learn.training:
            with torch.no_grad():
                preds, targs = F.softmax(self.learn.pred, dim=1), self.learn.y
                preds, targs = [x.detach().cpu().numpy().copy() for x in [preds,targs]]
                self.plot.do_plot(preds, targs)

# Cell
def image_and_bars(values, labels, image_url, title="Probabilities", height=225, width=500):
    """Plot an image along with a bar graph"""
    fig = go.Figure()
    fig.add_trace( go.Bar(x=labels, y=values, marker_color=["red","green","blue"]) )
    fig.add_layout_image(
        dict(
            source=image_url,
            xref="paper", yref="paper",
            x=-0.2, y=0.5,
            sizex=1, sizey=1,
            xanchor="right", yanchor="middle"
        )
    )
        # update layout properties
    fig.update_layout(
        autosize=False,
        height=height, width=width,
        bargap=0.15,
        bargroupgap=0.1,
        barmode="stack",
        hovermode="x",
        margin=dict(r=20, l=width*0.55, t=30, b=20),
        yaxis=dict(range=[0,1]),
        title={
        'text': title,
        'y':0.9,
        'x':0.76,
        'xanchor': 'center',
        'yanchor': 'bottom'}
    )
    return fig

# Cell

def sorted_eig(A):  # returns sorted eigenvalues (& their corresponding eignevectors) of A
    lambdas, vecs = LA.eig(A)
    # Next line just sorts values & vectors together in order of decreasing eigenvalues
    lambdas, vecs = zip(*sorted(zip(list(lambdas), list(vecs.T)),key=lambda x: x[0], reverse=True))
    return lambdas, np.array(vecs).T  # un-doing the list-casting from the previous line

def pca_proj(data, dim=3):
    """Projects data using Principal Component Analysis"""

    cov = np.cov(data.T)   # get covariance matrix
    lambdas, vecs = sorted_eig(np.array(cov))  # get the eigenvectors
    W = vecs[:,0:dim]                      # Grab the 2 most significant dimensions
    return np.array(data @ W, dtype=np.float32)  # Last step of PCA: projection