import psycopg2
import os
from datetime import timedelta
from google.cloud import storage
from google.oauth2 import service_account
from dotenv import load_dotenv
from logger import logger_init

logger = logger_init("database_logger", "application.log")
load_dotenv()

credentials = service_account.Credentials.from_service_account_file('./gcp_private_key.json')

def fetch_data(cursor):
    try:
        logger.info("Querying Store Status table")
        cursor.execute("SELECT store_id, status, timestamp_utc FROM storestatus;")
        store_status = cursor.fetchall()

        logger.info("Querying Store Timezone table")
        cursor.execute("SELECT store_id, timezone_str FROM storetimezone;")
        store_timezone = {row[0]: row[1] for row in cursor.fetchall()}

        logger.info("Querying Store Hours table")
        cursor.execute("SELECT store_id, day, start_time_local, end_time_local FROM storehours;")
        store_hours = {}
        for row in cursor.fetchall():
            if row[0] not in store_hours:
                store_hours[row[0]] = {}
            if row[1] not in store_hours[row[0]]:
                store_hours[row[0]][row[1]] = []
            store_hours[row[0]][row[1]].append({'start': row[2], 'end': row[3]})

        logger.info("Data fetched successfully.")
        return store_status, store_timezone, store_hours

    except Exception as e:
        logger.error(f"An error occurred while fetching data: {str(e)}")
        return [], {}, {}

def get_data():
    try:
        connection = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            dbname=os.getenv("POSTGRES_DB")
        )

        cursor = connection.cursor()
        store_status, store_timezone, store_hours = fetch_data(cursor)
        cursor.close()
        connection.close()

        logger.info("Connection closed successfully.")
        return store_status, store_timezone, store_hours

    except Exception as e:
        logger.error(f"An error occurred while getting data: {str(e)}")
        return [], {}, {}

def upload_report(report_id, csv_file):
    try:
        bucket_name = os.getenv("GCP_CLOUD_STORAGE_BUCKET")
        file_name = f"{report_id}.csv"
        
        storage_client = storage.Client(project="diesel-boulder-394818")
        bucket = storage_client.bucket(bucket_name)
        
        blob = bucket.blob(file_name)
        blob.upload_from_file(csv_file, content_type="text/csv")
        
        logger.info("Report generated and uploaded successfully.")
        
        return report_id
    
    except Exception as e:
        logger.error(f"An error occurred while uploading the report: {str(e)}")
        return
    
def generate_signed_url(bucket_name, file_name):
    storage_client = storage.Client(project="diesel-boulder-394818", credentials=credentials)

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    if not blob.exists():
        return None

    url = blob.generate_signed_url(expiration=timedelta(seconds=3600))

    return url

def get_report(report_id):
    bucket_name = os.getenv("GCP_CLOUD_STORAGE_BUCKET")
    file_name = f"{report_id}.csv"

    signed_url = generate_signed_url(bucket_name, file_name)

    return signed_url
