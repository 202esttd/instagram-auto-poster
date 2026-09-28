"""
Connection test: verifies your access token and account ID work.
It does NOT post anything. Run it from GitHub -> Actions -> "Check Connection".
"""
import os
import sys
import requests

GRAPH_API = "https://graph.instagram.com/v23.0"


def main():
    token = os.environ["IG_ACCESS_TOKEN"]
    ig_user_id = os.environ["IG_USER_ID"]

    resp = requests.get(
        f"{GRAPH_API}/{ig_user_id}",
        params={"fields": "username,account_type", "access_token": token},
    )
    print("Status code:", resp.status_code)
    print("Response:", resp.text)
    if resp.status_code != 200:
        print("\nFAILED: token or account ID is wrong/expired.")
        sys.exit(1)

    limit = requests.get(
        f"{GRAPH_API}/{ig_user_id}/content_publishing_limit",
        params={"fields": "quota_usage,config", "access_token": token},
    )
    print("\nPublishing limit check:", limit.status_code, limit.text)
    if limit.status_code != 200:
        print("\nWARNING: token may be missing the content_publish permission.")
        sys.exit(1)

    print("\nSUCCESS: connection and publish permission look good.")


if __name__ == "__main__":
    main()
