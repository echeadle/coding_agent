import random  # add this with your other imports at the top of the file

def request_with_retry(url, headers, payload, max_retries=10):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.exceptions.RequestException as e:
            wait_time = 2 ** attempt
            wait_time *= (1 + random.random() * 0.25)  # <-- here (network errors)
            print(f"Network error: {e}. Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
            continue

        if response.status_code == 429 or response.status_code >= 500:
            retry_after = response.headers.get("retry-after")
            try:
                wait_time = int(retry_after) if retry_after else 2 ** attempt
            except (ValueError, TypeError):
                wait_time = 2 ** attempt
            wait_time *= (1 + random.random() * 0.25)  # <-- here (rate limits/5xx)
            print(f"Error {response.status_code}. Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
            continue

        if response.status_code >= 400:
            try:
                error_msg = response.json()["error"]["message"]
            except (KeyError, ValueError):
                error_msg = response.text
            raise Exception(f"API error ({response.status_code}): {error_msg}")

        return response

    raise Exception(f"Request failed after {max_retries} retries")