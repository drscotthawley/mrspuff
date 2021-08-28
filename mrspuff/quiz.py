# AUTOGENERATED! DO NOT EDIT! File to edit: quiz.ipynb (unless otherwise specified).

__all__ = ['set_css_in_cell_output', 'detect_theme', 'cypher', 'decypher', 'mc_widget']

# Cell
import ipywidgets as widgets
from IPython.display import HTML, display, clear_output
import base64

# Cell

def set_css_in_cell_output():
    display(HTML('''
        <style>
            .jupyter-widgets {
                color: var(--colab-primary-text-color)
            }
            .jupyter-button {
                color: var(--colab-border-color)
            }
        </style>
    '''))

def detect_theme():  # change widget font color based on Colab theme
    '''ipywidgets by default outputs black text for everything. Hard to read in Dark theme.'''
    get_ipython().events.register('pre_run_cell', set_css_in_cell_output)

detect_theme()  # go ahead and execute detect_theme

# Cell

def cypher(text, decode=False, key='key'):
    '''Vigenère cipher: Not secure, just a way to not display plaintext'''
    # SHH modded from https://stackoverflow.com/a/38223403/4259243

    out, sign, offset = [], 1, 0
    if decode:
        sign, offset, text = -1, 256, base64.urlsafe_b64decode(text).decode()
    for i in range(len(text)):
        key_c = key[i % len(key)]
        out_c = chr((offset + ord(text[i]) + sign*ord(key_c)) % 256)
        out.append(out_c)
    if decode: return "".join(out)
    return base64.urlsafe_b64encode("".join(out).encode()).decode()

def decypher(text, key='key'):
    return cypher(text, decode=True, key=key)

# Cell

def mc_widget(description,       # text to be displayed first, e.g. the question to be asked
              options,           # the choices
              correct_answer,
              decrypt_correct=False):
    '''Multiple Choice question widget
    From zxzhaixiang's answer https://github.com/jupyter-widgets/ipywidgets/issues/2487#issuecomment-510721436
    Decrypt answer added by SHH
    '''
    if decrypt_correct: correct_answer = decypher(correct_answer)

    if correct_answer not in options:
        options.append(correct_answer)

    correct_answer_index = options.index(correct_answer)

    radio_options = [(words, i) for i, words in enumerate(options)]
    alternativ = widgets.RadioButtons(
        options = radio_options,
        description = '',
        disabled = False,
        layout={'width': 'max-content'}
    )


    description_out = widgets.Output()
    with description_out:
        if (description is not None) and ('' != description):
            print(description)

    feedback_out = widgets.Output()

    def check_selection(b):
        a = int(alternativ.value)
        if a==correct_answer_index:
            s = '\x1b[6;30;42m' + "Correct." + '\x1b[0m' +"\n" #green color
        else:
            s = '\x1b[5;30;41m' + "Incorrect. " + '\x1b[0m' +"\n" #red color
        with feedback_out:
            clear_output()
            print(s)
        return

    check = widgets.Button(description="submit")
    check.on_click(check_selection)

    return widgets.VBox([description_out, alternativ, check, feedback_out])