import json

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Apply CORS policy to the S3 media bucket"

    def add_arguments(self, parser):
        parser.add_argument(
            "--origins",
            nargs="+",
            default=["http://localhost:3000"],
            help="Allowed origins (space-separated). Defaults to http://localhost:3000.",
        )

    def handle(self, *args, **options):
        origins = options["origins"]
        cors_config = {
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "PUT"],
                    "AllowedOrigins": origins,
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3000,
                }
            ]
        }

        client = boto3.client(
            "s3",
            region_name=settings.AWS_S3_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        client.put_bucket_cors(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            CORSConfiguration=cors_config,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"CORS policy applied to bucket '{settings.AWS_S3_BUCKET_NAME}':\n"
                + json.dumps(cors_config, indent=2)
            )
        )
