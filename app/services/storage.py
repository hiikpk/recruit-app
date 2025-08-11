import os
from werkzeug.utils import secure_filename
from flask import current_app
import boto3
from botocore.client import Config


def _ensure_local_dir():
    d = current_app.config['LOCAL_STORAGE_DIR']
    os.makedirs(d, exist_ok=True)
    return d


def save_file(file_storage, prefix=""):
    backend = current_app.config.get('STORAGE_BACKEND','local')
    filename = secure_filename(file_storage.filename)
    key = f"{prefix}/{filename}" if prefix else filename

    if backend == 's3':
        s3 = boto3.client(
            's3',
            endpoint_url=current_app.config['S3_ENDPOINT'],
            aws_access_key_id=current_app.config['S3_ACCESS_KEY'],
            aws_secret_access_key=current_app.config['S3_SECRET_KEY'],
            config=Config(signature_version='s3v4')
        )
        bucket = current_app.config['S3_BUCKET']
        s3.upload_fileobj(file_storage, bucket, key)
        return f"s3://{bucket}/{key}"
    else:
        d = _ensure_local_dir()
        path = os.path.join(d, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        file_storage.save(path)
        return f"file://{os.path.abspath(path)}"


def download_bytes(url: str) -> bytes:
    if url.startswith('s3://'):
        bucket_key = url.replace('s3://','').split('/',1)
        bucket, key = bucket_key[0], bucket_key[1]
        s3 = boto3.client('s3',
            endpoint_url=current_app.config['S3_ENDPOINT'],
            aws_access_key_id=current_app.config['S3_ACCESS_KEY'],
            aws_secret_access_key=current_app.config['S3_SECRET_KEY'],
            config=Config(signature_version='s3v4'))
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj['Body'].read()
    elif url.startswith('file://'):
        path = url.replace('file://','')
        with open(path, 'rb') as f:
            return f.read()
    else:
        raise ValueError("Unsupported URL scheme")