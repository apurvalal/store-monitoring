import threading
import io
import pytz
import csv
import uuid
from datetime import datetime, timedelta
from models.database_model import get_data, upload_report, get_report
from logger import logger_init

logger = logger_init("report_services_logger", "application.log")

def fetch_report(report_id):
    signed_url = get_report(report_id)
    if signed_url:
        return signed_url
    else:
        return None
def trigger():
    # Generate a new report ID and start a thread to generate the report
    report_id = str(uuid.uuid4())
    report_thread = threading.Thread(target=generate, args=(report_id,))
    report_thread.start()
    return report_id

def generate(report_id):
    try:
        logger.info("Generating report")
        store_status, store_timezone, store_hours = get_data()
        processed_data = process_data(store_status, store_timezone)
        report_data = calculate_uptime_downtime(processed_data, store_hours, store_timezone)

        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['store_id', 'uptime_last_hour', 'uptime_last_day', 'uptime_last_week', 'downtime_last_hour', 'downtime_last_day', 'downtime_last_week'])
        writer.writerows(report_data)

        csv_file.seek(0)

        upload_report(report_id, csv_file)

        logger.info("Report generated successfully.")

    except Exception as e:
        logger.error(f"An error occurred while generating the report: {str(e)}")
        return


def process_data(store_status, store_timezone):
    processed_data = {}
    try:
        logger.info("Processing data")

        for row in store_status:
            store_id, status, timestamp_utc = row
            if store_id != "store_id":
                timestamp_str = timestamp_utc[:-4]
                timestamp = datetime.fromisoformat(timestamp_str)
                tz = pytz.timezone(store_timezone[store_id])
                local_time = timestamp.replace(tzinfo=pytz.utc).astimezone(tz)
                if store_id not in processed_data:
                    processed_data[store_id] = []
                processed_data[store_id].append({'status': status, 'timestamp': local_time})

        logger.info("Data processed successfully.")

    except Exception as e:
        logger.error(f"An error occurred while processing data: {str(e)}")
        return {}

    return processed_data

def calculate_overlap(start_time, end_time, business_hours_intervals):
    # Calculate the overlap between business hours and the given time range
    overlap = timedelta()
    for interval in business_hours_intervals:
        interval_start, interval_end = interval
        overlap_start = max(start_time, interval_start)
        overlap_end = min(end_time, interval_end)

        overlap += max(overlap_end - overlap_start, timedelta())
    return overlap

def update_time(status, overlap_time, uptime_var, downtime_var, start_time, last_time_local, seconds):
    # Update the uptime and downtime based on the overlap with business hours
    increment = overlap_time.total_seconds() / seconds if start_time >= last_time_local else 0
    if status:
        return (uptime_var + increment, downtime_var + (seconds - increment) / seconds)
    else:
        return (uptime_var + (seconds - increment) / seconds, downtime_var + increment)


def calculate_uptime_downtime(processed_data, store_hours, store_timezone):
    try:
        logger.info("Calculating uptime and downtime")
        report = []

        current_time = datetime.utcnow()
        # current_time = datetime.strptime('2023-01-26 10:04:30.823433', '%Y-%m-%d %H:%M:%S.%f')  - For Testing
        last_hour_time = current_time - timedelta(hours=1)
        last_day_time = current_time - timedelta(days=1)
        last_week_time = current_time - timedelta(weeks=1)

        for store_id, observations in processed_data.items():
            tz = pytz.timezone(store_timezone.get(store_id, 'UTC'))
            current_time_local = current_time.astimezone(tz)
            intervals = [
                ("hour", last_hour_time.astimezone(tz), current_time_local, 60),
                ("day", last_day_time.astimezone(tz), current_time_local, 24),
                ("week", last_week_time.astimezone(tz), current_time_local, 168),
            ]

            uptimes = {"hour": 0, "day": 0, "week": 0}
            downtimes = {"hour": 0, "day": 0, "week": 0}

            store_hours_intervals = store_hours.get(store_id, {'0': [{'start': '00:00:00', 'end': '23:59:59'}]})

            last_status = None
            last_timestamp = None

            for obs in observations:
                status = obs['status'] == 'active'
                timestamp = obs['timestamp']

                business_hours_intervals = []
                for business_hour in store_hours_intervals.get(str(timestamp.weekday()), [{'start': '00:00:00', 'end': '23:59:59'}]):
                    start_time = datetime.strptime(business_hour['start'], '%H:%M:%S').time()
                    end_time = datetime.strptime(business_hour['end'], '%H:%M:%S').time()
                    interval_start_time = timestamp.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
                    interval_end_time = timestamp.replace(hour=end_time.hour, minute=end_time.minute, second=59, microsecond=999999)
                    business_hours_intervals.append((interval_start_time, interval_end_time))

                if last_timestamp:
                    for name, start_time, end_time, scale_factor in intervals:
                        overlap_time = calculate_overlap(max(last_timestamp, start_time), min(timestamp, end_time), business_hours_intervals)

                        increment = overlap_time.total_seconds() / (3600 if name == "hour" else 3600)
                        increment /= scale_factor

                        if last_status: # if active status, increase uptime
                            uptimes[name] += increment
                        else: # if inactive status, increase downtime
                            downtimes[name] += increment

                last_status = status
                last_timestamp = timestamp

            report.append([store_id, min(uptimes["hour"], 60), min(uptimes["day"], 24), min(uptimes["week"], 168),
                           min(downtimes["hour"], 60), min(downtimes["day"], 24), min(downtimes["week"], 168)])

        logger.info("Uptime and downtime calculated successfully.")
        return report

    except Exception as e:
        logger.error(f"An error occurred while calculating uptime and downtime: {str(e)}")
        return []

