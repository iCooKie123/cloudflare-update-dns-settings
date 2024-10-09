import datetime
import http.client
import json
import os
from dotenv import load_dotenv
import logging
import subprocess

load_dotenv()

# Access environment variables
zone_id = os.getenv('zone_id')
dns_record_id = os.getenv('dns_record_id')
domain_name = os.getenv('domain_name')
auth_key = os.getenv('auth_key')
auth_email = os.getenv('auth_email')
ntfy_ip = os.getenv("ntfy_ip")
proxied = os.getenv('proxied') == "True"
ntfy_url = os.getenv("ntfy_url")
notify_on_pass=os.getenv("notify_on_pass") == "True"
current_date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
req_headers = {
    'Content-Type': "application/json",
    'X-Auth-Email': auth_email,
    'X-Auth-Key': auth_key
}

logging.basicConfig(
    filename='cloudflare_ip.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def send_ntfy_message(body_message):
    if ntfy_ip is None:
        return
    try:
        curl_command = [
            'curl', '-d', body_message, '-o', '/dev/null', '-s', '-w', '%{http_code}',
            "{}/{}".format(ntfy_ip, ntfy_url)
        ]

        # Run the curl command and capture output
        result = subprocess.run(curl_command, capture_output=True, text=True)

        # Check if the HTTP status code is not 200
        if result.stdout.strip() != '200':
            raise ValueError("Non-200 response: {}".format(result.stdout))

    except Exception as e:
        logging.error("Error pushing notification: {}".format(e))
        raise


def get_public_ip():
    try:
        aws_conn = http.client.HTTPSConnection("checkip.amazonaws.com")
        aws_conn.request("GET", "/")
        response_ip = aws_conn.getresponse()
        if response_ip.status != 200:
            raise ValueError(
                "Failed to get IP, status code: {}, message: {}".format(
                    response_ip.status, json.dumps(
                        json.loads(response_ip.read().decode()), indent=4)
                )
            )
        ip = response_ip.read().decode().strip()
        aws_conn.close()
        return ip
    except Exception as e:
        logging.error("Error getting public IP: {}".format(e))
        raise


def check_sameip(current_ip):
    try:
        cloudflare_conn = http.client.HTTPSConnection("api.cloudflare.com")
        cloudflare_conn.request(
            "GET", "/client/v4/zones/{}/dns_records/{}".format(zone_id, dns_record_id), headers=req_headers
        )
        response = cloudflare_conn.getresponse()
        if response.status != 200:
            raise ValueError(
                "Failed to check IP, status code: {}, message: {}".format(
                    response.status, json.dumps(json.loads(
                        response.read().decode()), indent=4)
                )
            )

        result = response.read().decode().strip()
        json_result = json.loads(result)
        dns_ip = json_result.get('result', {}).get('content', None)

        cloudflare_conn.close()
        return dns_ip == current_ip
    except Exception as e:
        logging.error("Error checking IP: {}".format(e))
        raise


def update_cloudflare_ip(public_ip):
    try:
        cloudflare_conn = http.client.HTTPSConnection("api.cloudflare.com")

        comment = "Updated on {}".format(current_date)

        content = public_ip
        payload = {
            "comment": comment,
            "name": domain_name,
            "proxied": proxied,
            "settings": {},
            "tags": [],
            "ttl": 1,
            "content": content,
            "type": "A"
        }

        json_payload = json.dumps(payload)

        cloudflare_conn.request(
            "PUT", "/client/v4/zones/{}/dns_records/{}".format(zone_id, dns_record_id), body=json_payload, headers=req_headers
        )

        res = cloudflare_conn.getresponse()
        if res.status != 200:
            raise ValueError(
                "Failed to update IP, status code: {}, message: {}".format(
                    res.status, json.dumps(json.loads(
                        res.read().decode()), indent=4)
                )
            )
        data = json.dumps(json.loads(res.read().decode()), indent=4)
        cloudflare_conn.close()
        return data
    except Exception as e:
        logging.error("Error updating Cloudflare IP: {}".format(e))
        raise


def main():
    try:
        current_ip = get_public_ip()
        same_ip = check_sameip(current_ip)
        if same_ip:
            logging.info(
                "Same IP detected ({}), not updating".format(current_ip))
            if notify_on_pass: send_ntfy_message("Same ip detected, not updating.")
        else:
            data = update_cloudflare_ip(current_ip)
            logging.info("Updated IP for {} to {}".format(
                domain_name, current_ip))
            logging.info("Response: " + data)

            send_ntfy_message("Updated ip to {}".format(current_ip))
    except Exception as e:
        logging.error("{}".format(e))
        send_ntfy_message(
            "There was an error while executing the script: {}".format(e)
        )


if __name__ == '__main__':
    main()
