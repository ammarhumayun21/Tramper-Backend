"""
Serializer mixins for common functionality.
"""

from rest_framework import serializers


class TimestampedSerializerMixin(serializers.Serializer):
    """
    Mixin that adds created_at and updated_at fields to serializers.
    """

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class TranslatedChoiceField(serializers.ChoiceField):
    """
    Custom choice field that translates choices.
    """

    def __init__(self, choices, **kwargs):
        super().__init__(choices=choices, **kwargs)

    def to_representation(self, value):
        """Return choice value with display name."""
        if value is None:
            return None
        return {
            "value": value,
            "display": dict(self.choices).get(value, value),
        }
