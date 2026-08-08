from prefect import serve

from app.core.config import PROCESS_JOB_DEPLOYMENT_NAME
from app.worker.flow import process_job


if __name__ == "__main__":
    serve(process_job.to_deployment(name=PROCESS_JOB_DEPLOYMENT_NAME))
