=======
Django GcalSync for mezzanine_events
=============

Sync application models with Google Calendar, so events created or edited in the Google Calendar web interface are automatically created/updated in your application. Helpful for situations were your application is the canonical record of event data created from various clients, including GC. To manage the categories(keywords) of events I used [eM Client](http://www.emclient.com/)

Authentication
----- 

If you haven't already, go to the [Google App Console](https://code.google.com/apis/console) and create an application. Create an OAuth2 Service account for your application, and get PK12 Key


Setup
-----

This needs to run as a demon/background process, and the assumption is that you're using (or will use) [django-celery](https://github.com/celery/django-celery) to accomplish this. 

Then...

Add `django-gcalsync` to your settings.py. 

Add a `GCALSYNC_CALENDAR` property to your settings.py - this should be Google calendar name created under the working Google account, and shared for your Service account email User.

 GCALSYNC_CALENDAR = 'primary'

Add a `GCALSYNC_CREDENTIALS` property to your settings.py - this should be the full path to the credentials file you created in Authentication above.

 GCALSYNC_CREDENTIALS = 'DIR/calendar.dat'

Add a `GCALSYNC_CREDENTIALS_EMAIL` property to your settings.py - this is the you `EMAIL ADDRESS` for Service Account in the Google App Console in Authentication

 GCALSYNC_CREDENTIALS_EMAIL = 'XXXXXXX-XXXXX@developer.gserviceaccount.com'

Add a `GCALSYNC_CREDENTIALS_KEY` property to your settings.py - this is the PK12 key generated in the Google App Console in Authentication, and converted to pem format

 GCALSYNC_CREDENTIALS_KEY = 'DIR/your-project-XXXXXXX.pem'

    openssl pkcs12 -in your-project-XXXXXXX.p12 -nodes -nocerts > your-project-XXXXXXX.pem (password:notasecret)

Assuming you're using [South](http://south.aeracode.org/), migrate models `python manage.py migrate django-gcalsync`

Run celery

    python manage.py celerybeat --log-level=info
    python manage.py celeryd —log-level=info


Usage
-----

Create a tasks.py module in the mezzanine_events. In that module you'll create a class responsible for transforming Google Calendar event data so it's usable by your model. Your class must have a `transform` method that accepts an event_data dictionary (the data from Google).



For Example:

    from __future__ import absolute_import
    from celery import shared_task
    from gcalsync.sync import Synchronizer
    from gcalsync.transformation import BaseTransformer
    from mezzanine_events.models import Event
    from mezzanine.conf import settings
    from rfc3339 import parse_date
    from mezzanine.generic.models import Keyword
    
    class EventTransformer(BaseTransformer):
        model = Event
    
        def transform(self, event_data):
            if not self.validate(event_data):
                return False
            res = {
                'title': event_data['summary'],
                'location': event_data['location'],
                'gcal_url': event_data['htmlLink'],
                'gcal_id': event_data['id'],
                'gcal_etag': event_data['etag']
            }
            if 'dateTime' in event_data['start']:
                start_datetime = self.parse_datetime(event_data['start']['dateTime'])
                res['start_date']= start_datetime.date()
                res['start_time']= start_datetime.time()
    
            elif 'date' in event_data['start']:
                res['start_date']= parse_date(event_data['start']['date'])
    
            if 'dateTime' in event_data['end']:
                end_datetime = self.parse_datetime(event_data['end']['dateTime'])
                res['end_date']= end_datetime.date()
                res['end_time']= end_datetime.time()
    
            elif 'date' in event_data['end']:
                res['end_date'] = parse_date(event_data['end']['date'])
    
            if 'description' in event_data:
                res['content'] = event_data['description']
    
            if 'extendedProperties' in event_data:
                if 'private' in event_data['extendedProperties']:
                    if 'X-MOZ-CATEGORIES' in event_data['extendedProperties']['private']:
                        res['keywords_string'] = event_data['extendedProperties']['private']['X-MOZ-CATEGORIES']
                        res['keywords'] = []
                        for keyword_string in res['keywords_string'].split(","):
                            res['keywords'].append(Keyword.objects.get_or_create(title=keyword_string)[0].id)
    
            return res
    
    @shared_task(ignore_result=True)
    def transform():
        synchronizer = Synchronizer(calendar_id=settings.GCALSYNC_CALENDAR, transformer=EventTransformer())
        synchronizer.sync()
    
