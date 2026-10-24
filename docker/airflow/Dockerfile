FROM apache/airflow:3.3.2-python3.12

COPY requirements.txt /requirements.txt

# Pinning apache-airflow keeps pip from up/downgrading Airflow while resolving.
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt
