# app/core/retry.py

from tenacity import retry, stop_after_attempt, wait_exponential

def with_retries():
    return retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(min=2, max=30),
        reraise=True,
    )
