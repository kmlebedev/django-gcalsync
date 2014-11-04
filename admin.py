from django.contrib import admin
from gcalsync.models import SyncedCalendar, SyncedEvent


class SyncedEventAdmin(admin.ModelAdmin):
    list_display = ('gcal_event_id', 'gcal_event_etag' , 'origin', "content_type", "content_object")

class SyncedCalendarAdmin(admin.ModelAdmin):
    list_display = ('calendar_id', "content_object")
    readonly_fields = ('calendar_id', "content_object" )

admin.site.register(SyncedCalendar, SyncedCalendarAdmin)
admin.site.register(SyncedEvent, SyncedEventAdmin)

