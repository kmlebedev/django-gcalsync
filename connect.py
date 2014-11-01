import httplib2
from oauth2client.file import Storage
from oauth2client.client import SignedJwtAssertionCredentials
from django.conf import settings
from apiclient.discovery import build

class Connection(object):
    service = None

    def get_service(self):
        if self.service:
            return self.service

        else:
            http = httplib2.Http()
            storage = Storage(settings.GCALSYNC_CREDENTIALS)
            credentials = storage.get()
            if credentials is None or credentials.invalid == True:
                    credentials = SignedJwtAssertionCredentials(settings.GCALSYNC_CREDENTIALS_EMAIL, settings.GCALSYNC_CREDENTIALS_KEY, scope="https://www.googleapis.com/auth/calendar")
                    storage.put(credentials)
            else:
                credentials.refresh(http)

            http = credentials.authorize(http)

            self.service =  build("calendar", "v3", http=http)
            return self.service
