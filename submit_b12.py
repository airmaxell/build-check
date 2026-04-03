import json
import os
import hmac
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone


def iso_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def main() -> None:
    applicant_name = os.environ["APPLICANT_NAME"]
    applicant_email = os.environ["APPLICANT_EMAIL"]
    resume_link = os.environ["RESUME_LINK"]

    github_server = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    github_repo = os.environ["GITHUB_REPOSITORY"]
    github_run_id = os.environ["GITHUB_RUN_ID"]

    repository_link = f"{github_server}/{github_repo}"
    action_run_link = f"{github_server}/{github_repo}/actions/runs/{github_run_id}"

    payload = {
        "timestamp": iso_timestamp(),
        "name": applicant_name,
        "email": applicant_email,
        "resume_link": resume_link,
        "repository_link": repository_link,
        "action_run_link": action_run_link,
    }

    # Canonical JSON: sorted keys, compact separators, UTF-8
    body = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    secret = os.getenv("B12_SIGNING_SECRET", "hello-there-from-b12").encode("utf-8")
    digest = hmac.new(secret, body, hashlib.sha256).hexdigest()
    signature = f"sha256={digest}"

    request = urllib.request.Request(
        url="https://b12.io/apply/submission",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Signature-256": signature,
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            response_text = response.read().decode("utf-8")
            print("Response:")
            print(response_text)
    except urllib.error.HTTPError as e:
        error_text = e.read().decode("utf-8", errors="replace")
        print(f"HTTP error: {e.code}")
        print(error_text)
        raise
    except urllib.error.URLError as e:
        print(f"Network error: {e}")
        raise

    data = json.loads(response_text)

    if not data.get("success") or "receipt" not in data:
        raise SystemExit("Submission failed: no valid receipt returned.")

    print(f"SUBMISSION_RECEIPT={data['receipt']}")


if __name__ == "__main__":
    main()