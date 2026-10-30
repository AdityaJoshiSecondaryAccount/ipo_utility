from django.db import models
from home.models import GroupDetail


class Contact(models.Model):
    phone_number = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200, blank=True, null=True)
    avatar_url = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contacts"

    def __str__(self):
        return f"{self.name or self.phone_number}"


class Conversation(models.Model):
    contact = models.OneToOneField(Contact, on_delete=models.CASCADE, related_name="conversation")
    group = models.ForeignKey(GroupDetail, on_delete=models.SET_NULL, null=True, blank=True, related_name="conversations")
    unread_count = models.IntegerField(default=0)
    last_message_text = models.TextField(blank=True, null=True)
    last_message_time = models.DateTimeField(auto_now_add=True, db_index=True)
    last_message_status = models.CharField(max_length=20, default="sent")
    last_inbound_time = models.DateTimeField(blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversations"

    def __str__(self):
        return f"Conversation with {self.contact.phone_number}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    wamid = models.CharField(max_length=100, unique=True, db_index=True, null=True, blank=True)
    direction = models.CharField(max_length=10)  # "inbound" or "outbound"
    message_type = models.CharField(max_length=20, default="text")
    text = models.TextField(blank=True, null=True)
    media_id = models.CharField(max_length=100, blank=True, null=True)
    media_url = models.CharField(max_length=1000, blank=True, null=True)
    media_mime_type = models.CharField(max_length=100, blank=True, null=True)
    media_filename = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, default="sent")
    error_message = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    raw_payload = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "messages"

    def __str__(self):
        return f"Message {self.id} [{self.direction}] ({self.message_type})"


class CannedResponse(models.Model):
    shortcut = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=100)
    body = models.TextField()
    category = models.CharField(max_length=50, default="General")

    class Meta:
        db_table = "canned_responses"

    def __str__(self):
        return f"{self.shortcut} - {self.title}"
