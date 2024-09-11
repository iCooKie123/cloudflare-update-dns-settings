import datetime
import http.client
import json
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Access environment variables
api_key = os.getenv('API_KEY')
zone_id = os.getenv('ZONE_ID')
dns_record_id = os.getenv('DNS_RECORD_ID')
domain_name = os.getenv('DOMAIN_NAME')
auth_key = os.getenv('AUTH_KEY')
auth_email = os.getenv('AUTH_EMAIL')
proxied = os.getenv("PROXIED")


current_date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
req_headers = {
    'Content-Type': "application/json",
    'X-Auth-Email': auth_email,
    'X-Auth-Key': api_key
}

logging.basicConfig(
    filename='cloudflare_ip.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def get_public_ip():
    try:
        aws_conn = http.client.HTTPSConnection("checkip.amazonaws.com")
        aws_conn.request("GET", "/")
        response_ip = aws_conn.getresponse()
        if response_ip.status != 200:
            raise ValueError(f"Failed to get IP, status code: {
                             response_ip.status}, message: {response_ip.read().decode()}")
        ip = response_ip.read().decode().strip()
        aws_conn.close()
        return ip
    except Exception as e:
        logging.error(f"Error getting public IP: {e}")
        raise


def check_sameip(current_ip):
    try:
        cloudflare_conn = http.client.HTTPSConnection("api.cloudflare.com")
        cloudflare_conn.request(
            "GET", f"/client/v4/zones/{zone_id}/dns_records/{dns_record_id}", headers=req_headers
        )
        response = cloudflare_conn.getresponse()

        if response.status != 200:
            raise ValueError(f"Failed to check IP, status code: {
                             response.status}, message: {response.read().decode()}")

        result = response.read().decode().strip()
        json_result = json.loads(result)
        dns_ip = json_result.get('result', {}).get('content', None)

        cloudflare_conn.close()
        return dns_ip == current_ip
    except Exception as e:
        logging.error(f"Error checking IP: {e}")
        raise


def update_cloudflare_ip(public_ip):
    try:
        cloudflare_conn = http.client.HTTPSConnection("api.cloudflare.com")

        comment = f"Updated on {current_date}"

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
            "PUT", f"/client/v4/zones/{zone_id}/dns_records/{
                dns_record_id}", json_payload, req_headers
        )

        res = cloudflare_conn.getresponse()
        if res.status != 200:
            raise ValueError(
                f"Failed to update IP, status code: {
                    res.status}, message: {res.read().decode()}"
            )

        data = res.read()
        cloudflare_conn.close()
        return data
    except Exception as e:
        logging.error(f"Error updating Cloudflare IP: {e}")
        raise


def main():
    try:
        current_ip = get_public_ip()
        same_ip = check_sameip(current_ip)
        if same_ip:
            logging.info(f"Same IP detected ({current_ip}), not updating")
        else:
            data = update_cloudflare_ip(current_ip)
            logging.info(f"Updated ip for {domain_name} to {current_ip}")
            logging.info("Response:"+data.decode("utf-8"))
    except Exception as e:
        logging.error(f"{e}")


if __name__ == '__main__':
    main()
