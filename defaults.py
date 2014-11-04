from mezzanine.conf import register_setting

register_setting(
    name="GCALSYNC_CALENDAR",
    description="The Google Calendar shared name to synchronization with",
    editable=True,
    default="primary",
)
