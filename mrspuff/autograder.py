#! /usr/bin/env python3

# standard imports:
import datetime
import requests
from dateutil.parser import parse as parsedate
import os, sys
import glob
import re
import argparse
import pandas as pd
import time
import subprocess
import smtplib

# You'll want to run: pip install yagmail pydrive2
import yagmail
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


"""
Purpose: This grabs certain parts of students' notebooks and combines them with
instructor-supplied imports and tests into a final .py file that is then run.

This relies on the Google Drive API and Gmail.
For GDrive you need Drive API oauth2 credentials.
For email you need to allow "Less Secure Apps" on Gmail or use some other SMTP-based service
Setting up a Google Drive App is nontrivial BTW. Good luck ;-)

First authenticate with Google by running:
    python pydrive2_auth.py

After that...

You supply these files:
    credentials.json              your Google Drive API oauth2 credentials
    settings.yaml                 Used by pydrive2
    assignment_{#}/imports.py     imports for this assignment
    assignment_{#}/tests.py       tests for this assignment
    valid_emails.txt              semicolong-separated list of student + instructor emails

    Command line usage is:
    ./autograder.py <assign_num> <sheets_url>


Also, I you need my function grabcolab() defined in your .bashrc or similar profile file:
    grabcolab() { fileid=$( echo "$1" | sed -E 's/.*drive\/(.*)\?.*/\1/' ); wget -q -U "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)" -O colab.ipynb 'https://docs.google.com/uc?export=download&id='$fileid; }


SECURITY NOTE:
    While efforts are made to limit imports and other powerful Python functions, and to
    trap for possible malicious input strings, this code is still very use-at-your-own-risk.
    It is recommended to only run this from a reduced-access account; even better would be
    to do so within a Docker container -- future feature?


---Scott H. Hawley, 11/30/2021
"""

## GLOBAL VARIABLES, which may be overwritten below by command-line args
sender_gmail = "FILL_ME_IN@gmail.com"   # ***FILL THIS IN***  Where results will be emailed from.
assign_num = 4      # changed via command line arg
assignment_dir = f"assignment_{assign_num}/"  # where notebooks gets downloaded to and were imports.py and tests.py live
ss_file = 'responses.csv'     # downloaded Google sheet is assigned to this local filename
valid_emails = []             # just so students don't have you emailing random people! ;-)



def get_valid_emails(email_file='valid_emails.txt'):
    "Reads list of semicolon-separated email addresses from file"
    email_list = []
    with open(email_file,'r') as f:
        email_str = f.read()
    if email_str != '':
        email_list = email_str.replace("\n","").replace(" ","").split(';')
    return email_list


def download_if_newer_generic(url, dst_file, force_new=False, date_key='Date'):
    """
    Only for generic, ordinary web-based files, not Google SaaS constructs like notebooks or sheets
    cf. https://stackoverflow.com/questions/29314287/python-requests-download-only-if-newer
    """
    r = requests.head(url)

    url_date = parsedate(r.headers[date_key]).astimezone()
    if not os.path.exists(dst_file):
        force_new = True
    else:
        file_date = datetime.datetime.fromtimestamp(os.path.getmtime(dst_file)).astimezone()
    print("url_date = ",url_date)
    print("file_date = ",file_date)
    if (force_new) or (url_date > file_date):
        print(f"Downloading {dst_file} from {url}...")
        user_agent = {"User-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:46.0) Gecko/20100101 Firefox/46.0"}
        r = requests.get(url, headers=user_agent)
        with open(dst_file, 'wb') as fd:
            for chunk in r.iter_content(4096):
                fd.write(chunk)

def ss_sharing_url_to_csv(url):
    "convert Google Sheets sharing url to csv url"
    return url.replace('edit?usp=sharing','gviz/tq?tqx=out:csv&sheet=Sheet1')


def url_to_id(url, split_ind=4):
    "convert google drive file url to file id"
    if 'spreadsheets' in url: split_ind = 5
    id =  url.split('/')[split_ind]
    id = id.replace('?usp=sharing','')
    return id

def gdrive_file_date(url):
    "get the last-modified data of a file on GDrive.  Requires API access and credentials"
    id = url_to_id(url)
    gd_file = drive.CreateFile({'id': id})
    gd_file.FetchMetadata(fields='modifiedDate')
    return parsedate(gd_file['modifiedDate']).astimezone()

def wait_til_file_ready(dst_file, sleep=1, timeout=20):
    "Literally just retries every sleep seconds, or times out after timeout seconds"
    start = time.time()
    while not os.path.exists(dst_file):
        dur = time.time() - start
        if dur > timeout: return False
        print(f"Waiting til file {dst_file} is ready. duration = {dur:3.0f}s, timeout at {timeout}s.")
        time.sleep(sleep)
    return True


def run_cmd(cmd, log=False, restricted=True):
    "run a unix shell command"
    # TODO: trap for possible problems when in restricted mode
    if log: print("    cmd = ",cmd)
    return subprocess.getoutput(cmd)


def download_if_newer_gdrive(url, dst_file, force_download=False, date_key='modifiedDate', colab=False):
    "Google Drive counterpart to download_if_newer_generic() above"
    updated, url_date = False, ''

    if not os.path.exists(dst_file):
        force_download = True
    else:
        file_date = datetime.datetime.fromtimestamp(os.path.getmtime(dst_file)).astimezone()

    if not force_download:  # no point checking date if we're going to force dl anyway
        url_date = gdrive_file_date(url)

    if (force_download) or (url_date > file_date):
        print(f"Downloading new version of {dst_file}")
        if colab:  # what we're downloading is a colab notebook
            cmd = f". ~/.bash_aliases && grabcolab {url} && mv colab.ipynb {dst_file}"
        else:      # other files
            cmd = f"rm -f {dst_file}; wget -q -U 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)' -O {dst_file} {url}"
        run_cmd(cmd)
        updated = True
    else:
        pass

    return updated


def skip_this_line(line, allow_imports=False):
    """Lots of lines in the notebook py file need not be copied into final code that gets run
    Even allowing student imports could be risky, e.g.
        import os as o
        o.system('rm -f *')
    """
    skip = False
    if (line == '') or (line == '\n'): skip = True    # skip blank lines
    prohibited = ['subprocess','fork','exec', 'popen','shutil',' os.c',' os.d',
        ' os.f',' os.g',' os.m',' os.pu',' os.r',' os.s',' os.u',
        'credentials.json','id_rsa']  # risky stuff, not allowed
    if any(s in line for s in prohibited): skip = True
    if (not allow_imports) and any(s in line for s in ['import ']): skip = True
    return skip


def grab_top_lev(pyfile, dir, debug=False, stop_after='token_to_one_hot', imports_wherever=True):
    """
    Student exercises will only occur inside functions and classes
    Grab relevant imports, function defs, or class defs
    IGNORES ANY OTHER TEXT -- esp. as it might generate syntax / IndentationError we don't care about
    """
    out_text = ''
    rec_start_cue = ' GRADED EXERCISE'
    block_name_cues = ['def','class']  # these all have to start in column 1
    also_allowed = ['nltk.']  # these all have to start in column 1

    file1 = open(pyfile, 'r')
    lines = file1.readlines()
    recording, already_found_stop = False, False
    block_started, block_name = False, ''    # block is a function or class
    for i, line in enumerate(lines):
        if skip_this_line(line): continue
        line = line.replace('\t','    ')  # convert tabs to spaces
        first_char, first_nonws_char, first_word = line[0], line.replace(' ','')[0], line.split(' ')[0]  # first things
        if first_nonws_char in ['!','%']: continue   # skip jupyter magics like !pip, %matplotlib

        if imports_wherever and (first_word in also_allowed):
            out_text += line
            continue

        # skip lines unindented comments except for the rec_start_cue
        if (first_char == '#') and (rec_start_cue not in line): continue

        if rec_start_cue in line:
            recording = True
            if debug: print(f"line = {line}. RECORDING = {recording}")
            out_text += '\n\n'   # cosmetic but nice
        elif recording:
            if (not imports_wherever) and (first_word in also_allowed):
                out_text += line
                continue
            if (not block_started) and (first_word in block_name_cues):
                block_started = True
                block_name = line.split(' ')[1].split('(')[0]
                print(f'    started block {block_name}')
            elif ((block_started) and (first_word in block_name_cues)) or (first_word != ''):
                block_started = False
                recording = False
                if debug: print(f"line = {line}. RECORDING = {recording}")
                if (block_name == stop_after):
                    if debug: print(f"line = {line}, reached end of stop_after={stop_after}.  Returning")
                    return out_text
        if recording: out_text += line
    return out_text



def clean_user_str(s:str):
    """Security: 's' is a user input that we'll end up using to name files and run shell commands,
    so we need to guard against injection attacks / arbitrary code execution"""
    disallowed_chars = [';','|','>','<','*']  # Google urls will use ?, &, / : a-zA-Z0-9, = btw
    escaped_chars = []
    for c in disallowed_chars: s = s.replace(c,'')   # remove
    for c in escaped_chars: s = s.replace(c,'\\'+c)   # escape via backslash
    return s


def run_nb(nb_file, funcs=['count_freqs']):
    "Run (parts of) the student's notebook"
    print(f"============\nConverting notebook: {nb_file}")
    pyfile = nb_file.replace('ipynb','py')
    dir = nb_file.split('/')[0]
    student_parts = f'{dir}/student_parts.py'  # where we'll save the grabbed parts of the student's file
    run_cmd(f'jupytext --to py {nb_file}')   # convert notebook to python script
    nb_py_text = grab_top_lev(pyfile, dir)  # grab the relevant parts of the student's code
    with open(student_parts, 'w') as f:
        f.write(nb_py_text)                 # write that to a text file called imports

    imports = assignment_dir+'/imports.py'                  # where predifed imports lie
    tests = assignment_dir+'/tests.py'                      # where my tests are written
    tester_file = f"test_assignment.py"      # paste students code and my tests together into this file
    run_cmd(f"cat {imports} {student_parts} {tests} > {tester_file}")
    print(f">>> Executing notebook: {tester_file}")
    run_log = run_cmd(f"python {tester_file}")
    run_log = f"Run log for {nb_file}:\n" + run_log
    if 'tests passed.' not in run_log[-20:]: run_log += "\n\n0 tests passed." # if the whole thing crashed
    print(run_log)
    return run_log



def send_email(to_addr, message, subject='DLAIE AUTOGRADER: Your results', from_addr=sender_gmail):
    "Emails student (or instructor)"
    if to_addr.lower() in valid_emails:
        print(f"Sending email to {to_addr}")
        # Note for gmail you need to set 'Allow less-secure apps' in Settings > Security
        yag = yagmail.SMTP(from_addr)  # yagmail only sends via gmail
        yag.send(to_addr, subject=subject, contents=message)
    else:
        print(f"ERROR: to_addr = {to_addr} not in list of valid emails: {valid_emails}")



def update_and_run_nb(row, dst_dir=assignment_dir, force_execute=False):
    "Grabs student notebook and tries to run it, and emails results"
    if not os.path.exists(dst_dir): os.mkdir(dst_dir)
    url, student_id, name, email = row['colab_url'],   row['student_id'].title(),  row['name'].title(), row['email'].lower()
    [url, student_id, name]  = [clean_user_str(x) for x in [url, student_id, name]]  # email isn't used in shell cmds
    for already in []: # can be used to skip over certain students' work, when testing/debugging
        if already in name:
            print(f"name = {name}. Already did this one ({already}). Returning.")
            return
    if 'usp=sharing' not in url:
        send_email(email, f"Error: Invalid sharing URL = {url}.\n You did not supply a 'sharing url' as instructed. Please edit your resonse to the web form.",
            subject=f'Autograder error: Invalid Colab URL')
        return
    dst_file = f"{dst_dir}/{student_id}_{name.replace(' ','_')}.ipynb"
    dst_file = clean_user_str(dst_file)   # just being extra careful / paranoid
    updated = download_if_newer_gdrive( url, dst_file, colab=True)
    if updated or force_execute:
        file_ready = wait_til_file_ready(dst_file)
        if file_ready:
            print("   ....")
            run_log = run_nb(dst_file)
            send_email(email, run_log)  # email to student
            #print("run_log = \n",run_log)
            send_email('scott.hawley@belmont.edu', run_log, subject=f'Autograder results for {name}')
        else:
            send_email(email, f"Error: Timeout. Unable to download notebook {url}.\nDid you remember to enable sharing with 'Anyone can View'?",
                subject=f'Autograder error: TIMEOUT')


### MAIN EXECUTION ####
if __name__=="__main__":

    parser = argparse.ArgumentParser(description='Run the autograder.')
    parser.add_argument('num', metavar='N', type=int, help='assignment number')
    parser.add_argument('url', type=str, help='sharing URL of Google Sheet')
    args = parser.parse_args()
    assign_num = args.num
    ss_url = args.url
    assignment_dir = f"assignment_{assign_num}/"  # where notebooks gets downloaded to and were imports.py and tests.py live


    print(f"Assignment {assign_num}, Sheets URL = {ss_url}")

    valid_emails = get_valid_emails()
    print(f"valid_emails = ",valid_emails)

    # authenticate for gdrive downloads
    print("Authorizing")
    gauth = GoogleAuth()
    print("Setting drive")
    drive = GoogleDrive(gauth)

    ## Update local copy of Google Forms spreadsheet
    print("\nChecking Google Forms spreadsheet for changes")
    csv_url = ss_sharing_url_to_csv(ss_url)
    download_if_newer_gdrive(csv_url, ss_file)

    ## Read in Google Forms spreadsheet
    wait_til_file_ready(ss_file)
    df = pd.read_csv(ss_file, header=None, names=['form_sub_date','name','student_id','email','colab_url']).drop([0])

    ## Update & run students' Colab notebooks
    print("\nChecking student notebooks for changes")
    df.apply(update_and_run_nb, axis=1)

### EOF
