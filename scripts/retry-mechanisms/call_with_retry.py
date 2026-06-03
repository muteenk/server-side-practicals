import functools
import random
import time

import requests

URL = "http://127.0.0.1:8000/retry-mechanisms/unreliable"
MAX_ATTEMPTS = 5
DELAY_SECONDS = 1
RETRYABLE = {429, 502, 503, 504}


########## API CALLER FUNCTION ###########
def call_api(url: str, timeout: int = 15):
    response = requests.get(url, timeout=timeout)
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}
    return {
        "status_code": response.status_code,
        "body": body,
        "headers": response.headers,
    }

########## UTILITY FUNCTIONS ###########
def finished(response):
    """Stop and return body on success or non-retryable error. None = try again."""
    status = response["status_code"]
    if status == 200 or status not in RETRYABLE:
        return response["body"]
    return None


def retry_after_wait(response):
    raw = response["headers"].get("Retry-After", DELAY_SECONDS)
    return float(raw)


####################
#  RETRY FUNCTIONS 
####################

def call_with_retry():
    """
    Most basic form of retry logic, retries are repeatedly done
    until the maximum number of attempts is reached.
    """
    for _ in range(MAX_ATTEMPTS):
        try:
            print(f"Attempt {_ + 1} of {MAX_ATTEMPTS}")
            body = finished(call_api(URL))
            if body is not None:
                return body
        except requests.exceptions.Timeout as e:
            print(f"Timeout: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
    return None


def call_with_retry_delay():
    """
    Calls the API with retry logic.
    This is a basic delay based retry mechanism, where delay is fixed and 
    retry is done after that fixed wait time.
    """
    for attempt in range(MAX_ATTEMPTS):
        try:
            print(f"Attempt {attempt + 1} of {MAX_ATTEMPTS}")
            body = finished(call_api(URL))
            if body is not None:
                return body
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(DELAY_SECONDS)
        except requests.exceptions.Timeout as e:
            print(f"Timeout: {e}")
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(DELAY_SECONDS)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
    return None


def call_with_retry_after():
    """
    Calls the API with retry after logic.
    The delay after each retry is the value of the Retry-After header.
    This is a more sophisticated retry mechanism,
    where the delay is the value of the Retry-After header.
    """
    for attempt in range(MAX_ATTEMPTS):
        try:
            print(f"Attempt {attempt + 1} of {MAX_ATTEMPTS}")
            response = call_api(URL)
            body = finished(response)
            if body is not None:
                return body
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(retry_after_wait(response))
        except requests.exceptions.Timeout as e:
            print(f"Timeout: {e}")
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(DELAY_SECONDS)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
    return None


def call_with_linear_backoff():
    """
    Calls the API with linear backoff logic.
    The delay after each retry is linearly increased.
    This is a simple retry mechanism, where the delay is increased
    after each retry, and the delay is not fixed.
    """
    for attempt in range(MAX_ATTEMPTS):
        try:
            body = finished(call_api(URL))
            if body is not None:
                return body
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(DELAY_SECONDS * (attempt + 1))
        except requests.exceptions.Timeout as e:
            print(f"Timeout: {e}")
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(DELAY_SECONDS * (attempt + 1))
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
    return None


def call_with_exponential_backoff():
    """
    Calls the API with exponential backoff logic.
    The delay after each retry is exponentially increased.
    This is a much more effective retry mechanism, where the delay is increased
    after each retry, and the delay is not fixed.
    """
    for attempt in range(MAX_ATTEMPTS):
        try:
            print(f"Attempt {attempt + 1} of {MAX_ATTEMPTS}")
            body = finished(call_api(URL))
            if body is not None:
                return body
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(DELAY_SECONDS * 2**attempt)
        except requests.exceptions.Timeout as e:
            print(f"Timeout: {e}")
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(DELAY_SECONDS * 2**attempt)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
    return None


def call_with_jitter():
    """
    Calls the API with jitter logic.
    The delay after each retry is randomly increased.
    This is a randomised delay based retry pattern, where the delay is randomly increased
    after each retry.
    """
    for attempt in range(MAX_ATTEMPTS):
        try:
            print(f"Attempt {attempt + 1} of {MAX_ATTEMPTS}")
            body = finished(call_api(URL))
            if body is not None:
                return body
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(DELAY_SECONDS * random.randint(1, 10))
        except requests.exceptions.Timeout as e:
            print(f"Timeout: {e}")
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(DELAY_SECONDS * random.randint(1, 10))
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
    return None


def call_with_jitter_and_backoff():
    """
    Calls the API with jitter and backoff logic.
    The delay after each retry is randomly increased and exponentially increased.
    This is most sophisticated and production ready retry mechanism, where the delay is randomly increased
    and exponentially increased after each retry.
    """
    for attempt in range(MAX_ATTEMPTS):
        try:
            print(f"Attempt {attempt + 1} of {MAX_ATTEMPTS}")
            body = finished(call_api(URL))
            if body is not None:
                return body
            if attempt < MAX_ATTEMPTS - 1:
                wait = DELAY_SECONDS * 2**attempt * random.randint(1, 10)
                time.sleep(wait)
        except requests.exceptions.Timeout as e:
            print(f"Timeout: {e}")
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(DELAY_SECONDS * 2**attempt * random.randint(1, 10))
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
    return None


def retry(max_attempts=MAX_ATTEMPTS, delay_seconds=DELAY_SECONDS):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    print(f"Attempt {attempt + 1} of {max_attempts}")
                    body = finished(func(*args, **kwargs))
                    if body is not None:
                        return body
                    if attempt < max_attempts - 1:
                        time.sleep(delay_seconds)
                except requests.exceptions.Timeout as e:
                    print(f"Timeout: {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(delay_seconds)
                except requests.exceptions.RequestException as e:
                    print(f"Error: {e}")
                    return None
            return None
        return wrapper
    return decorator


@retry()
def fetch_unreliable_api():
    return call_api(URL)


if __name__ == "__main__":
    print(fetch_unreliable_api())
