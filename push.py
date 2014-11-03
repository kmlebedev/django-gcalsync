import time
import rfc3339
from tzlocal import get_localzone
from celery.task import task

from gcalsync.connect import Connection
from gcalsync.models import SyncedEvent, SyncedCalendar

from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import localtime, make_aware
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

class Pusher(object):
    def __init__(self, model):
        self.model = model

    def get_event_data(self):
        event_data = self.set_dates(self.model.to_gcal())
        event_data['status'] = 'confirmed'

        return event_data

    def set_dates(self, event_data):
        tz = get_localzone()
        if 'dateTime' in event_data['start']:
            start_dt_aware = tz.localize(event_data['start']['dateTime'])
            event_data['start']['dateTime'] = rfc3339.datetimetostr(start_dt_aware)
        elif 'date' in event_data['start']:
            event_data['start']['date'] = event_data['start']['date'].isoformat()

        if 'dateTime' in event_data['end']:
            end_dt_aware = tz.localize(event_data['end']['dateTime'])
            event_data['end']['dateTime'] = rfc3339.datetimetostr(end_dt_aware)
        elif 'date' in event_data['end']:
            event_data['end']['date'] = event_data['end']['date'].isoformat()

        return event_data

    def create_or_update(self):
        service = Connection().get_service()
        content_type = ContentType.objects.get_for_model(self.model)
        event_data = self.get_event_data()
        calendar_id = event_data.pop('calendarId')

        try:
            synced_event = SyncedEvent.objects.get(content_type=content_type, object_id=self.model.id)


            if synced_event.origin == 'google':
                return False

            g_event = service.events().patch(calendarId=calendar_id, 
                eventId=synced_event.gcal_event_id, body=event_data).execute()

            return g_event

        except SyncedEvent.DoesNotExist:
            g_event = service.events().insert(calendarId=calendar_id, 
                body=event_data).execute()

            synced_calendar, created = SyncedCalendar.objects.get_or_create(calendar_id=calendar_id)

            synced_event = SyncedEvent.objects.create(
                    content_object=self.model,
                    gcal_event_id=g_event['id'],
                    gcal_event_url=g_event['htmlLink'],
                    synced_calendar=synced_calendar,
                    origin='app'
                )

            return g_event

@task(ignore_result=True, default_retry_delay=10)
def async_push_to_gcal(instance):
    logger.info(u'Start asycn push event %s to google calendar' % instance.title )
    Pusher(instance).create_or_update()

