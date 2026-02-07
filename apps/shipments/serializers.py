"""
Shipment serializers for Tramper.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Shipment, ShipmentItem, Dimension
from core.storage import s3_storage
from core.serializers import LocationSerializer
from core.models import Location


class DimensionSerializer(serializers.ModelSerializer):
    """Serializer for dimensions."""

    class Meta:
        model = Dimension
        fields = [
            "id",
            "height",
            "width",
            "length",
            "unit",
        ]
        read_only_fields = ["id"]


class ShipmentItemSerializer(serializers.ModelSerializer):
    """Serializer for shipment items."""

    id = serializers.UUIDField(required=False)
    dimensions = DimensionSerializer(required=False, allow_null=True)
    total_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    total_weight = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text=_("List of item images (will be uploaded to S3)"),
    )

    class Meta:
        model = ShipmentItem
        fields = [
            "id",
            "name",
            "link",
            "category",
            "quantity",
            "single_item_price",
            "single_item_weight",
            "weight_unit",
            "dimensions",
            "image_urls",
            "images",
            "total_price",
            "total_weight",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["image_urls", "created_at", "updated_at"]

    def create(self, validated_data):
        """Create shipment item with dimensions and handle image uploads."""
        dimensions_data = validated_data.pop("dimensions", None)
        images = validated_data.pop("images", [])
        
        # Create dimensions if provided
        dimensions = None
        if dimensions_data:
            dimensions = Dimension.objects.create(**dimensions_data)
            validated_data["dimensions"] = dimensions
        
        # Create shipment item
        item = ShipmentItem.objects.create(**validated_data)
        
        # Upload images to S3 if provided
        if images:
            image_urls = []
            for image in images:
                try:
                    url = s3_storage.upload_image(image, folder="shipment_items")
                    image_urls.append(url)
                except Exception as e:
                    print(f"Failed to upload image: {str(e)}")
            
            if image_urls:
                item.image_urls = image_urls
                item.save(update_fields=['image_urls'])
        
        return item

    def update(self, instance, validated_data):
        """Update shipment item with dimensions and handle image uploads."""
        dimensions_data = validated_data.pop("dimensions", None)
        images = validated_data.pop("images", [])
        
        # Update dimensions if provided
        if dimensions_data:
            if instance.dimensions:
                for attr, value in dimensions_data.items():
                    setattr(instance.dimensions, attr, value)
                instance.dimensions.save()
            else:
                dimensions = Dimension.objects.create(**dimensions_data)
                instance.dimensions = dimensions
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle image updates: delete old images and upload new ones
        if images:
            # Delete old images from S3
            old_urls = instance.image_urls or []
            for old_url in old_urls:
                try:
                    s3_storage.delete_image(old_url)
                except Exception as e:
                    print(f"Failed to delete old image: {str(e)}")
            
            # Upload new images to S3
            image_urls = []
            for image in images:
                try:
                    url = s3_storage.upload_image(image, folder="shipment_items")
                    image_urls.append(url)
                except Exception as e:
                    print(f"Failed to upload image: {str(e)}")
            
            # Replace with new URLs
            instance.image_urls = image_urls
            instance.save(update_fields=['image_urls'])
        
        return instance


class ShipmentSerializer(serializers.ModelSerializer):
    """Serializer for shipment data."""

    items = ShipmentItemSerializer(many=True, read_only=True)
    sender_id = serializers.UUIDField(source="sender.id", read_only=True)
    traveler_id = serializers.UUIDField(source="traveler.id", read_only=True, allow_null=True)

    class Meta:
        model = Shipment
        fields = [
            "id",
            "sender_id",
            "traveler_id",
            "name",
            "notes",
            "status",
            "from_location",
            "to_location",
            "travel_date",
            "items",
            "reward",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "sender_id", "created_at", "updated_at"]
    
    def to_representation(self, instance):
        """Return complete location objects in response."""
        data = super().to_representation(instance)
        # Replace location UUIDs with full objects
        if instance.from_location:
            data['from_location'] = LocationSerializer(instance.from_location).data
        if instance.to_location:
            data['to_location'] = LocationSerializer(instance.to_location).data
        return data


class ShipmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing shipments."""

    sender_id = serializers.UUIDField(source="sender.id", read_only=True)
    traveler_id = serializers.UUIDField(source="traveler.id", read_only=True, allow_null=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            "id",
            "sender_id",
            "traveler_id",
            "name",
            "status",
            "from_location",
            "to_location",
            "travel_date",
            "reward",
            "items_count",
            "created_at",
        ]
        read_only_fields = ["id", "sender_id", "created_at"]

    def get_items_count(self, obj):
        """Get count of items in shipment."""
        return obj.items.count()
    
    def to_representation(self, instance):
        """Return complete location objects in response."""
        data = super().to_representation(instance)
        # Replace location UUIDs with full objects
        if instance.from_location:
            data['from_location'] = LocationSerializer(instance.from_location).data
        if instance.to_location:
            data['to_location'] = LocationSerializer(instance.to_location).data
        return data


class ShipmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating shipments with items."""

    items = ShipmentItemSerializer(many=True)
    from_location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    to_location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())

    class Meta:
        model = Shipment
        fields = [
            "name",
            "notes",
            "status",
            "from_location",
            "to_location",
            "travel_date",
            "items",
            "reward",
        ]

    def create(self, validated_data):
        """Create shipment with items."""
        items_data = validated_data.pop("items")
        shipment = Shipment.objects.create(**validated_data)
        
        # Create items
        for item_data in items_data:
            dimensions_data = item_data.pop("dimensions", None)
            images = item_data.pop("images", [])
            
            # Create dimensions if provided
            if dimensions_data:
                dimensions = Dimension.objects.create(**dimensions_data)
                item_data["dimensions"] = dimensions
            
            # Create item
            item = ShipmentItem.objects.create(shipment=shipment, **item_data)
            
            # Upload images
            if images:
                image_urls = []
                for image in images:
                    try:
                        url = s3_storage.upload_image(image, folder="shipment_items")
                        image_urls.append(url)
                    except Exception as e:
                        print(f"Failed to upload image: {str(e)}")
                
                if image_urls:
                    item.image_urls = image_urls
                    item.save(update_fields=['image_urls'])
        
        return shipment


class ShipmentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating shipments."""

    items = ShipmentItemSerializer(many=True, required=False)
    from_location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all(), required=False)
    to_location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all(), required=False)

    class Meta:
        model = Shipment
        fields = [
            "name",
            "notes",
            "status",
            "from_location",
            "to_location",
            "travel_date",
            "reward",
            "traveler",
            "items",
        ]
        extra_kwargs = {
            "traveler": {"required": False},
        }

    def update(self, instance, validated_data):
        """Update shipment and its items."""
        items_data = validated_data.pop("items", None)
        
        # Update shipment fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items if provided
        if items_data is not None:
            # Get existing items
            existing_items = list(instance.items.all())
            existing_items_by_id = {str(item.id): item for item in existing_items}
            
            # Check if any items have IDs (update mode) or none have IDs (replace mode)
            has_ids = any(item_data.get("id") for item_data in items_data)
            
            if not has_ids and existing_items:
                # Replace mode: no IDs provided, update existing items by index
                # or delete extra items if fewer items provided
                for index, item_data in enumerate(items_data):
                    item_data.pop("id", None)  # Remove id if present
                    dimensions_data = item_data.pop("dimensions", None)
                    images = item_data.pop("images", [])
                    
                    if index < len(existing_items):
                        # Update existing item at this index
                        item = existing_items[index]
                        
                        # Update dimensions
                        if dimensions_data:
                            if item.dimensions:
                                for attr, value in dimensions_data.items():
                                    setattr(item.dimensions, attr, value)
                                item.dimensions.save()
                            else:
                                item.dimensions = Dimension.objects.create(**dimensions_data)
                        
                        # Update item fields
                        for attr, value in item_data.items():
                            setattr(item, attr, value)
                        item.save()
                        
                        # Handle images
                        if images:
                            old_urls = item.image_urls or []
                            for old_url in old_urls:
                                try:
                                    s3_storage.delete_image(old_url)
                                except Exception as e:
                                    print(f"Failed to delete old image: {str(e)}")
                            
                            image_urls = []
                            for image in images:
                                try:
                                    url = s3_storage.upload_image(image, folder="shipment_items")
                                    image_urls.append(url)
                                except Exception as e:
                                    print(f"Failed to upload image: {str(e)}")
                            
                            item.image_urls = image_urls
                            item.save(update_fields=['image_urls'])
                    else:
                        # Create new item
                        if dimensions_data:
                            dimensions = Dimension.objects.create(**dimensions_data)
                            item_data["dimensions"] = dimensions
                        
                        item = ShipmentItem.objects.create(shipment=instance, **item_data)
                        
                        if images:
                            image_urls = []
                            for image in images:
                                try:
                                    url = s3_storage.upload_image(image, folder="shipment_items")
                                    image_urls.append(url)
                                except Exception as e:
                                    print(f"Failed to upload image: {str(e)}")
                            
                            if image_urls:
                                item.image_urls = image_urls
                                item.save(update_fields=['image_urls'])
                
                # Delete extra existing items if fewer items provided
                if len(items_data) < len(existing_items):
                    for item in existing_items[len(items_data):]:
                        # Delete images from S3
                        for url in (item.image_urls or []):
                            try:
                                s3_storage.delete_image(url)
                            except Exception:
                                pass
                        item.delete()
            else:
                # ID-based update mode
                for item_data in items_data:
                    item_id = item_data.pop("id", None)
                    dimensions_data = item_data.pop("dimensions", None)
                    images = item_data.pop("images", [])
                    
                    if item_id and str(item_id) in existing_items_by_id:
                        # Update existing item
                        item = existing_items_by_id[str(item_id)]
                        
                        # Update dimensions
                        if dimensions_data:
                            if item.dimensions:
                                for attr, value in dimensions_data.items():
                                    setattr(item.dimensions, attr, value)
                                item.dimensions.save()
                            else:
                                item.dimensions = Dimension.objects.create(**dimensions_data)
                        
                        # Update item fields
                        for attr, value in item_data.items():
                            setattr(item, attr, value)
                        item.save()
                        
                        # Handle images - delete old and upload new
                        if images:
                            old_urls = item.image_urls or []
                            for old_url in old_urls:
                                try:
                                    s3_storage.delete_image(old_url)
                                except Exception as e:
                                    print(f"Failed to delete old image: {str(e)}")
                            
                            image_urls = []
                            for image in images:
                                try:
                                    url = s3_storage.upload_image(image, folder="shipment_items")
                                    image_urls.append(url)
                                except Exception as e:
                                    print(f"Failed to upload image: {str(e)}")
                            
                            item.image_urls = image_urls
                            item.save(update_fields=['image_urls'])
                    else:
                        # Create new item
                        if dimensions_data:
                            dimensions = Dimension.objects.create(**dimensions_data)
                            item_data["dimensions"] = dimensions
                        
                        item = ShipmentItem.objects.create(shipment=instance, **item_data)
                        
                        if images:
                            image_urls = []
                            for image in images:
                                try:
                                    url = s3_storage.upload_image(image, folder="shipment_items")
                                    image_urls.append(url)
                                except Exception as e:
                                    print(f"Failed to upload image: {str(e)}")
                            
                            if image_urls:
                                item.image_urls = image_urls
                                item.save(update_fields=['image_urls'])
        
        return instance

