# this is the "quickstart" file recommended in PyDrive2 docs
from pydrive2.auth import GoogleAuth

gauth = GoogleAuth()
print("authorization worked, now calling LocalWebserverAuth")
gauth.LocalWebserverAuth() # Creates local webserver and auto handles authentication.

