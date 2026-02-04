"""
S3 storage utility for Tramper.
Simple interface for uploading images to AWS S3.
"""

import boto3
import uuid
from django.conf import settings
from botocore.exceptions import ClientError


class S3Storage:
    """Simple S3 storage handler for uploading files."""

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    def upload_image(self, file, folder="images"):
        """
        Upload an image file to S3.
        
        Args:
            file: Django UploadedFile object
            folder: S3 folder/prefix (default: "images")
            
        Returns:
            str: Public URL of the uploaded image
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Generate unique filename
            file_extension = file.name.split('.')[-1]
            unique_filename = f"{folder}/{uuid.uuid4()}.{file_extension}"
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                unique_filename,
                ExtraArgs={
                    'ContentType': file.content_type
                }
            )
            
            # Return public URL
            url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{unique_filename}"
            return url
            
        except ClientError as e:
            raise Exception(f"Failed to upload image to S3: {str(e)}")

    def delete_image(self, image_url):
        """
        Delete an image from S3 by its URL.
        
        Args:
            image_url: Full S3 URL of the image
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            # Extract key from URL
            key = image_url.split(f"{settings.AWS_S3_CUSTOM_DOMAIN}/")[-1]
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False


# Singleton instance
s3_storage = S3Storage()
