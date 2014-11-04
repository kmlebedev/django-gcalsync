from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from model_utils import Choices

class SyncedCalendar(models.Model):
    calendar_id = models.CharField(max_length=100, unique=True, db_index=True)
    last_synced = models.DateTimeField(blank=True, null=True)
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        return self.calendar_id

class SyncedEvent(models.Model):
    ORIGINS = Choices('app','google')

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    gcal_event_id = models.CharField(max_length=100,unique=True, db_index=True)
    gcal_event_etag = models.CharField(max_length=100)
    gcal_event_url = models.URLField(max_length=512,blank=True, null=True)
    origin = models.CharField(choices=ORIGINS,default=ORIGINS.google,max_length=6)
    synced_calendar = models.ForeignKey(SyncedCalendar)

    def __unicode__(self):
        return '%s from %s' %(self.gcal_event_id, self.synced_calendar.calendar_id)