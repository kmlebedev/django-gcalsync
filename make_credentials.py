from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import SignedJwtAssertionCredentials

import httplib2
import pprint

f = file("D:/projects/academschool16/deploy/academschool16-mezzanine-d97bd08977d2.pem", "rb")
key = f.read()
f.close()
storage = Storage("D:/projects/academschool16/deploy/calendar.dat")
credentials = storage.get()
http = httplib2.Http()
if credentials is None or credentials.invalid == True:
  #credentials = run(FLOW, storage)
    credentials = SignedJwtAssertionCredentials(
    "619079679308-9qre6t41rs758pvkjptbiiumm0fgg4kp@developer.gserviceaccount.com", key,
    scope="https://www.googleapis.com/auth/calendar"
    )
    storage.put(credentials)
else:
    credentials.refresh(http)

# Create an authorized http instance

http = credentials.authorize(http)

# Create a service call to the calendar API
service = build("calendar", "v3", http=http)
#admin@academschool16.ru
lists = service.calendarList().list(pageToken=None).execute(http=http)
pprint.pprint(lists)
