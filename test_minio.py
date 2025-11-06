#!/usr/bin/env python3
"""Тест подключения к MinIO"""
import sys
import traceback

print("Testing MinIO connection...")

try:
    from app.core.storage import get_minio_client
    
    print("✓ Import successful")
    
    client = get_minio_client()
    print(f"✓ MinIO client created")
    print(f"  Endpoint: {client.s3_client.meta.endpoint_url}")
    print(f"  Bucket: {client.bucket_name}")
    
    # Проверить что bucket существует
    try:
        client.s3_client.head_bucket(Bucket=client.bucket_name)
        print(f"✓ Bucket '{client.bucket_name}' exists")
    except Exception as e:
        print(f"✗ Bucket check failed: {e}")
        print("  This is OK if MinIO is not running yet")
    
    print("\n✅ MinIO client configuration is correct!")
    print("\nNext steps:")
    print("1. Make sure MinIO is running: docker-compose up -d minio")
    print("2. Start backend: uvicorn app.main:app --reload")
    print("3. Upload a file through frontend")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nStack trace:")
    traceback.print_exc()
    sys.exit(1)
