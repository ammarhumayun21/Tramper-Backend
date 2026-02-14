# Generated migration for Category model
# This migration:
# 1. Creates the Category model
# 2. Renames old category field to category_name
# 3. Adds new category FK field

from django.db import migrations, models
import django.db.models.deletion
import uuid


def populate_categories_and_link(apps, schema_editor):
    """Populate categories from the CATEGORIES_DATA and link existing items."""
    Category = apps.get_model('shipments', 'Category')
    ShipmentItem = apps.get_model('shipments', 'ShipmentItem')
    
    # 50 Categories for Shipment Items
    CATEGORIES_DATA = [
        {"name": "Electronics", "description": "Electronic devices and accessories", "icon": "📱"},
        {"name": "Clothing", "description": "Apparel and fashion items", "icon": "👕"},
        {"name": "Books", "description": "Books, magazines, and printed materials", "icon": "📚"},
        {"name": "Documents", "description": "Official documents and papers", "icon": "📄"},
        {"name": "Cosmetics", "description": "Beauty and personal care products", "icon": "💄"},
        {"name": "Jewelry", "description": "Jewelry and precious accessories", "icon": "💍"},
        {"name": "Toys", "description": "Children's toys and games", "icon": "🧸"},
        {"name": "Food", "description": "Non-perishable food items", "icon": "🍫"},
        {"name": "Medicine", "description": "Medical supplies and pharmaceuticals", "icon": "💊"},
        {"name": "Shoes", "description": "Footwear of all types", "icon": "👟"},
        {"name": "Bags", "description": "Handbags, backpacks, and luggage", "icon": "👜"},
        {"name": "Watches", "description": "Watches and timepieces", "icon": "⌚"},
        {"name": "Glasses", "description": "Eyewear and sunglasses", "icon": "👓"},
        {"name": "Accessories", "description": "Fashion accessories", "icon": "🎀"},
        {"name": "Sports Equipment", "description": "Sports and fitness gear", "icon": "⚽"},
        {"name": "Musical Instruments", "description": "Musical instruments and accessories", "icon": "🎸"},
        {"name": "Art Supplies", "description": "Art and craft materials", "icon": "🎨"},
        {"name": "Home Decor", "description": "Decorative items for home", "icon": "🖼️"},
        {"name": "Kitchen Items", "description": "Kitchen utensils and gadgets", "icon": "🍳"},
        {"name": "Baby Products", "description": "Baby care and nursery items", "icon": "👶"},
        {"name": "Pet Supplies", "description": "Pet food and accessories", "icon": "🐕"},
        {"name": "Office Supplies", "description": "Stationery and office equipment", "icon": "📎"},
        {"name": "Computer Parts", "description": "Computer hardware and components", "icon": "💻"},
        {"name": "Phone Accessories", "description": "Mobile phone cases and accessories", "icon": "📱"},
        {"name": "Camera Equipment", "description": "Cameras and photography gear", "icon": "📷"},
        {"name": "Video Games", "description": "Gaming consoles and video games", "icon": "🎮"},
        {"name": "DVDs & Blu-rays", "description": "Movies and entertainment media", "icon": "📀"},
        {"name": "Musical Albums", "description": "Music CDs and vinyl records", "icon": "💿"},
        {"name": "Tools", "description": "Hardware tools and equipment", "icon": "🔧"},
        {"name": "Garden Supplies", "description": "Gardening tools and seeds", "icon": "🌱"},
        {"name": "Automotive Parts", "description": "Car parts and accessories", "icon": "🚗"},
        {"name": "Bicycle Parts", "description": "Bicycle components and accessories", "icon": "🚴"},
        {"name": "Camping Gear", "description": "Outdoor and camping equipment", "icon": "⛺"},
        {"name": "Fishing Equipment", "description": "Fishing rods and tackle", "icon": "🎣"},
        {"name": "Collectibles", "description": "Collectible items and memorabilia", "icon": "🏆"},
        {"name": "Antiques", "description": "Antique and vintage items", "icon": "🕰️"},
        {"name": "Handicrafts", "description": "Handmade crafts and artisan goods", "icon": "🧵"},
        {"name": "Furniture Parts", "description": "Furniture components and hardware", "icon": "🪑"},
        {"name": "Textiles", "description": "Fabrics and textile materials", "icon": "🧶"},
        {"name": "Electrical Supplies", "description": "Electrical components and wiring", "icon": "🔌"},
        {"name": "Plumbing Supplies", "description": "Plumbing parts and fixtures", "icon": "🚰"},
        {"name": "Paint & Supplies", "description": "Paint and painting supplies", "icon": "🖌️"},
        {"name": "Photography Prints", "description": "Printed photographs and artwork", "icon": "🖼️"},
        {"name": "Souvenirs", "description": "Travel souvenirs and memorabilia", "icon": "🗿"},
        {"name": "Religious Items", "description": "Religious articles and gifts", "icon": "📿"},
        {"name": "Seasonal Items", "description": "Holiday and seasonal decorations", "icon": "🎄"},
        {"name": "Party Supplies", "description": "Party decorations and supplies", "icon": "🎉"},
        {"name": "Educational Materials", "description": "Educational books and materials", "icon": "📖"},
        {"name": "Scientific Equipment", "description": "Scientific instruments and supplies", "icon": "🔬"},
        {"name": "Other", "description": "Miscellaneous items", "icon": "📦"},
    ]
    
    # Create categories
    category_map = {}
    for cat_data in CATEGORIES_DATA:
        category, _ = Category.objects.get_or_create(
            name=cat_data["name"],
            defaults={
                "description": cat_data["description"],
                "icon": cat_data["icon"],
            }
        )
        category_map[cat_data["name"].lower()] = category
    
    # Get or create "Other" category as fallback
    other_category = category_map.get("other")
    
    # Link existing shipment items to categories
    for item in ShipmentItem.objects.all():
        if item.category_name:
            # Try to find matching category (case-insensitive)
            category_key = item.category_name.lower().strip()
            category = category_map.get(category_key)
            
            # If no exact match, try to find partial match
            if not category:
                for key, cat in category_map.items():
                    if category_key in key or key in category_key:
                        category = cat
                        break
            
            # Use "Other" if still no match
            if not category:
                category = other_category
            
            item.category = category
            item.save()


def reverse_migration(apps, schema_editor):
    """Reverse migration - nothing to do for data."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('shipments', '0002_alter_shipment_from_location_and_more'),
    ]

    operations = [
        # Step 1: Create Category model
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='name')),
                ('description', models.TextField(blank=True, null=True, verbose_name='description')),
                ('icon', models.CharField(blank=True, help_text='Icon name or emoji for the category', max_length=50, null=True, verbose_name='icon')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
            ],
            options={
                'verbose_name': 'category',
                'verbose_name_plural': 'categories',
                'ordering': ['name'],
            },
        ),
        # Step 2: Rename old category field to category_name
        migrations.RenameField(
            model_name='shipmentitem',
            old_name='category',
            new_name='category_name',
        ),
        # Step 3: Make category_name nullable
        migrations.AlterField(
            model_name='shipmentitem',
            name='category_name',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='category name (deprecated)'),
        ),
        # Step 4: Add new category FK field
        migrations.AddField(
            model_name='shipmentitem',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='shipment_items', to='shipments.category', verbose_name='category'),
        ),
        # Step 5: Run data migration to populate categories and link items
        migrations.RunPython(populate_categories_and_link, reverse_migration),
    ]
