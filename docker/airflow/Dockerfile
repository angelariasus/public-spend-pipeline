FROM apache/airflow:3.3.2-python3.12

COPY requirements.txt requirements-dbt.txt /

# Pinning apache-airflow keeps pip from up/downgrading Airflow while resolving.
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

# dbt gets its own virtualenv so its dependency pins never clash with Airflow's.
USER root
RUN PIP_USER=false python -m venv /opt/dbt-venv \
    && PIP_USER=false /opt/dbt-venv/bin/pip install --no-cache-dir -r /requirements-dbt.txt
USER airflow
