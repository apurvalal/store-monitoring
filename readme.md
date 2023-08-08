# Store Monitoring

### Link to video: https://www.loom.com/share/1d10fefc82da403789a63009f5038b57?sid=a10258e6-8a6d-4019-a46f-186d1728e141

## Overview

This project is designed to track and analyze the uptime and downtime of various stores within their business hours. The generated report includes the uptime and downtime statistics for the last hour, day, and week, and provides two main API endpoints: triggering the report and fetching an existing report.

## Components

### 1. **Endpoints**

#### 1.1. `/trigger_report` (GET)

- **Purpose**: Trigger a new report generation.
- **Response**: Returns the report ID or raises a 400 HTTP Exception if an error occurs.

#### 1.2. `/get_report` (POST)

- **Input**: `report_id` - The ID of the report to be fetched.
- **Purpose**: Fetch an existing report using its ID.
- **Response**: Returns the report url and status as COMPLETE if complete, or status as RUNNNING if still running. Raises a 400 HTTP Exception if an error occurs.

### 2. **Database Model**
Database is stored in GCP CloudSQL as PostgreSQL database. There are three tables: store_timezone(primary_key: store_id), store_status(references: store_timezone.store_id) and store_hours(references: store_timezone.store_id)

The report is uploaded on GCP Storage and a link is generated for the csv file.

### 3. **Logic**
#### 3.1. **Initialization of Time Intervals**

- Current time is defined.
- Time intervals for the last hour, day, and week are calculated.
- Uptime and downtime counters for these intervals are initialized to zero.
#### 3.2. **Processing Observations**
- The data for each store is processed, and the observations are sorted by time.
- The store's status (active or inactive) and its timestamp are extracted from the observation.
- Business hours are retrieved and adjusted according to the store's local timezone.
#### 3.3. **Calculating Overlaps with Business Hours**
- For each observation, the code calculates the overlap between the store's business hours and the intervals defined earlier (hour, day, week).
- The calculate_overlap function computes the overlap time by comparing the start and end times of the business hours with the intervals.

#### 3.4. **Updating Uptime and Downtime Metrics**
- The update_time function computes the uptime and downtime for each interval, taking into account the overlap with business hours.
- If the store status is active, the uptime is incremented based on the overlap time.
- If the store status is inactive, the downtime is incremented based on the overlap time.
- The increments are scaled according to the interval's total seconds (e.g., 3600 seconds for an hour).

#### 3.5. **Filling Intervals with Interpolation**
- It calculates the uptime and downtime for the entire interval based on the observations and their overlap with the business hours.
- For example, if there are two observations for a store on a Monday from 10:14 AM to 11:15 AM, and the business hours are from 9 AM to 12 PM, the code uses the two observations to calculate the uptime and downtime for the entire business hours.

#### 3.6. **Finalizing Report Data**
- The calculated uptimes and downtimes are capped to the maximum possible values for the intervals (e.g., 60 for an hour).
- The data is then appended to the report, which includes metrics for uptime and downtime for the last hour, day, and week for each store.

## Tech Stack
- **Language**: Python
- **Web Framework**: FastAPI
- **Database**: PostgreSQL - psycopg2 module
- **Cloud Storage**: Google Cloud Storage - google-cloud-storage module
- **Logging**: logging (python's logging module)
- **Environment Management**: dotenv

## Usage

### Installation

Ensure all the required libraries and environment variables are properly set up:

- FastAPI
- psycopg2
- google-cloud-storage
- python-dotenv

### Running the Application

Launch the FastAPI application by running the main file. The endpoints will be accessible at `/api/trigger_report` and `/api/get_report`.

## Error Handling

Exception handling and logging are incorporated to catch and record errors throughout the process, ensuring robust operation.

## Output

The final report is generated as a CSV file and stored in Google Cloud Storage. The URL to access the report is provided when requested via the `/get_report` endpoint.

## Database Schema

- **storestatus**: Contains the store_id, status, timestamp_utc.
- **storetimezone**: Contains the store_id, timezone_str.
- **storehours**: Contains the store_id, day, start_time_local, end_time_local.