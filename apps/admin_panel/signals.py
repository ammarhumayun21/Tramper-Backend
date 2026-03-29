"""
Django signals for automatic activity logging.
Tracks create, update, delete, and status changes across all models.
"""

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver

from apps.trips.models import Trip
from apps.shipments.models import Shipment
from apps.requests.models import Request
from apps.users.models import User
from apps.verification.models import VerificationRequest
from apps.chatrooms.models import ChatRoom
from apps.payments.models import Payment
from .models import ActivityLog


# ============================================================================
# PRE-SAVE: Cache old values for status change detection
# ============================================================================

def _cache_old_instance(sender, instance, **kwargs):
    """Cache old instance data for comparison in post_save."""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_status = getattr(old, "status", None)
            instance._old_is_active = getattr(old, "is_active", None)
            instance._is_new = False
        except sender.DoesNotExist:
            instance._is_new = True
            instance._old_status = None
            instance._old_is_active = None
    else:
        instance._is_new = True
        instance._old_status = None
        instance._old_is_active = None


pre_save.connect(_cache_old_instance, sender=Trip)
pre_save.connect(_cache_old_instance, sender=Shipment)
pre_save.connect(_cache_old_instance, sender=Request)
pre_save.connect(_cache_old_instance, sender=User)
pre_save.connect(_cache_old_instance, sender=VerificationRequest)
pre_save.connect(_cache_old_instance, sender=ChatRoom)
pre_save.connect(_cache_old_instance, sender=Payment)


# ============================================================================
# TRIP SIGNALS
# ============================================================================

@receiver(post_save, sender=Trip)
def log_trip_activity(sender, instance, created, **kwargs):
    """Log trip create and status change events."""
    trip = instance
    from_loc = str(trip.from_location) if trip.from_location_id else "Unknown"
    to_loc = str(trip.to_location) if trip.to_location_id else "Unknown"
    traveler_name = trip.first_name or "A traveler"

    if created or getattr(instance, "_is_new", False):
        ActivityLog.objects.create(
            actor_id=trip.traveler_id,
            action="created",
            entity_type="trip",
            entity_id=trip.pk,
            description=f"{traveler_name} created a new trip: {from_loc} → {to_loc}",
            metadata={"status": trip.status},
        )
    else:
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != trip.status:
            ActivityLog.objects.create(
                actor_id=trip.traveler_id,
                action="status_changed",
                entity_type="trip",
                entity_id=trip.pk,
                description=f"{traveler_name}'s trip {from_loc} → {to_loc} status changed: {old_status} → {trip.status}",
                metadata={"old_status": old_status, "new_status": trip.status},
            )


@receiver(post_delete, sender=Trip)
def log_trip_delete(sender, instance, **kwargs):
    """Log trip deletion."""
    trip = instance
    traveler_name = trip.first_name or "A traveler"
    from_loc = str(trip.from_location) if trip.from_location_id else "Unknown"
    to_loc = str(trip.to_location) if trip.to_location_id else "Unknown"

    ActivityLog.objects.create(
        actor_id=trip.traveler_id,
        action="deleted",
        entity_type="trip",
        entity_id=trip.pk,
        description=f"{traveler_name}'s trip {from_loc} → {to_loc} was deleted",
    )


# ============================================================================
# SHIPMENT SIGNALS
# ============================================================================

@receiver(post_save, sender=Shipment)
def log_shipment_activity(sender, instance, created, **kwargs):
    """Log shipment create and status change events."""
    shipment = instance
    sender_name = str(shipment.sender) if shipment.sender_id else "A user"
    from_loc = str(shipment.from_location) if shipment.from_location_id else "Unknown"
    to_loc = str(shipment.to_location) if shipment.to_location_id else "Unknown"

    if created or getattr(instance, "_is_new", False):
        ActivityLog.objects.create(
            actor_id=shipment.sender_id,
            action="created",
            entity_type="shipment",
            entity_id=shipment.pk,
            description=f"{sender_name} created a new shipment: {from_loc} → {to_loc}",
            metadata={"status": shipment.status, "reward": str(shipment.reward)},
        )
    else:
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != shipment.status:
            status_messages = {
                "accepted": f"{shipment.name} shipment has been accepted",
                "in_transit": f"{shipment.name} shipment is now in transit",
                "delivered": f"{shipment.name} shipment was delivered to {to_loc}",
                "received": f"{shipment.name} shipment was received at {to_loc}",
                "cancelled": f"{shipment.name} shipment was cancelled",
            }
            desc = status_messages.get(
                shipment.status,
                f"{shipment.name} status changed: {old_status} → {shipment.status}",
            )
            ActivityLog.objects.create(
                actor_id=shipment.sender_id,
                action="status_changed",
                entity_type="shipment",
                entity_id=shipment.pk,
                description=desc,
                metadata={"old_status": old_status, "new_status": shipment.status},
            )


@receiver(post_delete, sender=Shipment)
def log_shipment_delete(sender, instance, **kwargs):
    """Log shipment deletion."""
    ActivityLog.objects.create(
        actor_id=instance.sender_id,
        action="deleted",
        entity_type="shipment",
        entity_id=instance.pk,
        description=f"{instance.name} shipment was deleted",
    )


# ============================================================================
# REQUEST SIGNALS
# ============================================================================

@receiver(post_save, sender=Request)
def log_request_activity(sender, instance, created, **kwargs):
    """Log request create and status change events."""
    req = instance
    sender_name = str(req.sender) if req.sender_id else "A user"
    receiver_name = str(req.receiver) if req.receiver_id else "A user"

    if created or getattr(instance, "_is_new", False):
        ActivityLog.objects.create(
            actor_id=req.sender_id,
            action="created",
            entity_type="request",
            entity_id=req.pk,
            description=f"{sender_name} sent a request to {receiver_name}",
            metadata={
                "status": req.status,
                "offered_price": str(req.offered_price),
            },
        )
    else:
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != req.status:
            ActivityLog.objects.create(
                actor_id=req.sender_id,
                action="status_changed",
                entity_type="request",
                entity_id=req.pk,
                description=f"Request from {sender_name} to {receiver_name} status changed: {old_status} → {req.status}",
                metadata={"old_status": old_status, "new_status": req.status},
            )


@receiver(post_delete, sender=Request)
def log_request_delete(sender, instance, **kwargs):
    """Log request deletion."""
    ActivityLog.objects.create(
        actor_id=instance.sender_id,
        action="deleted",
        entity_type="request",
        entity_id=instance.pk,
        description=f"Request from {instance.sender} to {instance.receiver} was deleted",
    )


# ============================================================================
# USER SIGNALS
# ============================================================================

@receiver(post_save, sender=User)
def log_user_activity(sender, instance, created, **kwargs):
    """Log user registration and account status changes."""
    user = instance
    display_name = user.full_name or user.username

    if created or getattr(instance, "_is_new", False):
        ActivityLog.objects.create(
            actor_id=user.pk,
            action="created",
            entity_type="user",
            entity_id=user.pk,
            description=f"{display_name} registered as a new user",
            metadata={"email": user.email},
        )
    else:
        old_is_active = getattr(instance, "_old_is_active", None)
        if old_is_active is not None and old_is_active != user.is_active:
            action_word = "activated" if user.is_active else "deactivated"
            ActivityLog.objects.create(
                actor=None,
                action="status_changed",
                entity_type="user",
                entity_id=user.pk,
                description=f"{display_name}'s account was {action_word}",
                metadata={
                    "old_is_active": old_is_active,
                    "new_is_active": user.is_active,
                },
            )


@receiver(post_delete, sender=User)
def log_user_delete(sender, instance, **kwargs):
    """Log user deletion."""
    display_name = instance.full_name or instance.username
    ActivityLog.objects.create(
        actor=None,
        action="deleted",
        entity_type="user",
        entity_id=instance.pk,
        description=f"{display_name}'s account was deleted",
    )


# ============================================================================
# VERIFICATION REQUEST SIGNALS
# ============================================================================

@receiver(post_save, sender=VerificationRequest)
def log_verification_activity(sender, instance, created, **kwargs):
    """Log verification request creation and status changes."""
    vr = instance
    user_email = str(vr.user) if vr.user_id else "A user"

    if created or getattr(instance, "_is_new", False):
        ActivityLog.objects.create(
            actor_id=vr.user_id,
            action="created",
            entity_type="verification",
            entity_id=vr.pk,
            description=f"{user_email} submitted a verification request",
        )
    else:
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != vr.status:
            ActivityLog.objects.create(
                actor_id=vr.reviewed_by_id,
                action="status_changed",
                entity_type="verification",
                entity_id=vr.pk,
                description=f"Verification for {user_email}: {old_status} → {vr.status}",
                metadata={"old_status": old_status, "new_status": vr.status},
            )


@receiver(post_delete, sender=VerificationRequest)
def log_verification_delete(sender, instance, **kwargs):
    """Log verification request deletion."""
    ActivityLog.objects.create(
        actor=None,
        action="deleted",
        entity_type="verification",
        entity_id=instance.pk,
        description=f"Verification request for {instance.user} was deleted",
    )


# ============================================================================
# CHATROOM SIGNALS
# ============================================================================

@receiver(post_save, sender=ChatRoom)
def log_chatroom_activity(sender, instance, created, **kwargs):
    """Log chatroom creation and disable events."""
    chatroom = instance
    sender_name = str(chatroom.sender) if chatroom.sender_id else "Unknown"
    receiver_name = str(chatroom.receiver) if chatroom.receiver_id else "Unknown"

    if created or getattr(instance, "_is_new", False):
        ActivityLog.objects.create(
            actor=None,
            action="created",
            entity_type="chatroom",
            entity_id=chatroom.pk,
            description=f"Chatroom created between {sender_name} and {receiver_name}",
            metadata={"is_active": chatroom.is_active},
        )
    else:
        old_is_active = getattr(instance, "_old_is_active", None)
        if old_is_active is not None and old_is_active != chatroom.is_active:
            if not chatroom.is_active:
                ActivityLog.objects.create(
                    actor=None,
                    action="status_changed",
                    entity_type="chatroom",
                    entity_id=chatroom.pk,
                    metadata={"old_is_active": old_is_active, "new_is_active": chatroom.is_active},
                )


# ============================================================================
# PAYMENT SIGNALS
# ============================================================================

@receiver(post_save, sender=Payment)
def log_payment_activity(sender, instance, created, **kwargs):
    """Log payment creation and status changes."""
    payment = instance
    payer_name = payment.user.full_name or payment.user.username if payment.user else "A user"
    
    if created or getattr(instance, "_is_new", False):
        ActivityLog.objects.create(
            actor_id=payment.user_id,
            action="created",
            entity_type="payment",
            entity_id=payment.pk,
            description=f"{payer_name} initiated a payment of {payment.currency} {payment.amount}",
            metadata={"status": payment.status, "amount": str(payment.amount)},
        )
    else:
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != payment.status:
            status_messages = {
                "completed": f"Payment by {payer_name} for {payment.currency} {payment.amount} was completed",
                "failed": f"Payment by {payer_name} for {payment.currency} {payment.amount} failed",
                "cancelled": f"Payment by {payer_name} for {payment.currency} {payment.amount} was cancelled",
            }
            desc = status_messages.get(
                payment.status,
                f"Payment by {payer_name} status changed: {old_status} → {payment.status}",
            )
            ActivityLog.objects.create(
                actor_id=payment.user_id,
                action="status_changed",
                entity_type="payment",
                entity_id=payment.pk,
                description=desc,
                metadata={"old_status": old_status, "new_status": payment.status},
            )


@receiver(post_delete, sender=Payment)
def log_payment_delete(sender, instance, **kwargs):
    """Log payment deletion."""
    payer_name = instance.user.full_name or instance.user.username if instance.user else "A user"
    ActivityLog.objects.create(
        actor_id=instance.user_id,
        action="deleted",
        entity_type="payment",
        entity_id=instance.pk,
        description=f"Payment by {payer_name} for {instance.currency} {instance.amount} was deleted",
    )
