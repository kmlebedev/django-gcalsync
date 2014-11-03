import datetime
import rfc3339

from django.conf import settings
from mezzanine.generic.models import AssignedKeyword, Keyword

from gcalsync.models import SyncedCalendar, SyncedEvent
from gcalsync.push import async_push_to_gcal
from gcalsync.connect import Connection
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
from pprint import pprint

class Retriever(object):
    def get_event_list(self, connection=None, calendar_id=None, 
        processor=None, last_retrieved=None, post_retrieval=None):
        
        page_token = None
        if last_retrieved:
            updated_min = rfc3339.datetimetostr(last_retrieved)
        else:
            updated_min = None

        _events = connection.get_service().events()
        while True:
            if updated_min:
                events = _events.list(calendarId=calendar_id, pageToken=page_token, updatedMin=updated_min).execute()
            else:
                events = _events.list(calendarId=calendar_id, showDeleted=False).execute()

            if events['items']:
                for event in events['items']:
                    processor(event)

            page_token = events.get('nextPageToken')
            if not page_token:
                post_retrieval()
                break
        logger.info(u'Get %i events  last modification time %s from calendar %s' % (len(events['items']), updated_min, str(calendar_id)))


class Synchronizer(object):
    def __init__(self, **kwargs):
        self.calendar_id = kwargs['calendar_id']
        self.transformer = kwargs['transformer']
        self.synced_calendar = self.setup_synced_calendar()

    def setup_synced_calendar(self):
        synced_calendar, created = SyncedCalendar.objects.get_or_create(
            calendar_id=self.calendar_id)

        return synced_calendar

    def sync(self):
        Retriever().get_event_list(connection=Connection(), 
            calendar_id=self.calendar_id, 
            processor=self.process,
            post_retrieval=self.post_retrieval,
            last_retrieved=self.synced_calendar.last_synced
        )

    def post_retrieval(self):
        self.synced_calendar.last_synced = datetime.datetime.now()
        self.synced_calendar.save()

    def get_model_data(self, event_data):
        return self.transformer.transform(event_data)

    def extract_gcal_data(self, model_data):
        gcal_event_etag = model_data.pop('gcal_etag', None)
        gcal_event_id = model_data.pop('gcal_id', None)
        gcal_event_url = model_data.pop('gcal_url', None)

        return gcal_event_etag, gcal_event_id, gcal_event_url

    def cancelled_synced_event(self,gcal_event_id):
        try:
            synced_event = SyncedEvent.objects.get(gcal_event_id=gcal_event_id, origin='google')
        except SyncedEvent.DoesNotExist:
            synced_event = None

        if synced_event:
            synced_event.content_object.delete()
            synced_event.delete()

    def create_synced_event(self, gcal_event_etag, gcal_event_id, model_data):
        try:
            synced_event = SyncedEvent.objects.get(gcal_event_id=gcal_event_id)
            event_model = synced_event.content_object
            if gcal_event_etag != synced_event.gcal_event_etag:
                for key,val in model_data.iteritems():
                    if hasattr(event_model, key):
                        if key == 'keywords':
                            try:
                                event_model.keywords.all().delete()
                            except:
                                pass
                            for keyword in val:
                                event_model.keywords.add(AssignedKeyword(keyword_id=keyword))
                        else:
                            setattr(event_model, key, val)

                logger.info(u'Synced event_model %s' % (event_model.title))
                event_model.save()

        except SyncedEvent.DoesNotExist:
            keywords = model_data.pop('keywords', None)
            synced_event = SyncedEvent(gcal_event_etag=gcal_event_etag,gcal_event_id=gcal_event_id, origin='google')
            event_model = self.transformer.model.objects.create(**model_data)
            if keywords:
                for keyword in keywords:
                    event_model.keywords.add(AssignedKeyword(keyword_id=keyword))
            synced_event.content_object = event_model
            synced_event.synced_calendar = self.synced_calendar
            synced_event.save()

        return synced_event           

    def process(self, event_data):
        model_data = self.get_model_data(event_data)
        if 'status' in event_data and 'id' in event_data:
            if event_data['status'] == 'cancelled':
                self.cancelled_synced_event(event_data['id'])
                return True

        if not model_data:
            logger.info(u'Error get model from event: %s' % pprint(event_data))
            return False

        gcal_event_etag, gcal_event_id, gcal_event_url = self.extract_gcal_data(model_data)

        if not gcal_event_id or not gcal_event_etag:
            logger.info(u'Error get id and etag from model event %s' % (event_data['summary']))
            return False

        synced_event = self.create_synced_event(gcal_event_etag, gcal_event_id, model_data)

        synced_event.gcal_event_url = gcal_event_url
        synced_event.gcal_event_etag = gcal_event_etag
        synced_event.save()
        logger.info(u'Synced event %s' % (event_data['summary']))

def push_to_gcal(sender, instance, **kwargs):
    async_push_to_gcal.delay(instance)
