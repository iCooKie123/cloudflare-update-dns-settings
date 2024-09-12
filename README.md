This python script is used to update Cloudflare DNS settings. It only supports one dns name at the time, so the only way to update multiple ones right now is to have multiple instances of this script.

You **need** to create the `.env` file that should have the following syntax:

```py
zone_id =  "your cloudflare id"
dns_record_id = "your cloudfare dns_record_id"
domain_name = "mydomain.example.com"
auth_key = "cloudfare_api_key"
auth_email = "test@example.com"
ntfy_ip = "optional, base url/ip of ntfy instance (e.g ntfy.sh)"
ntfy_url = "optional, the subscribed topic you want to send the notification to (e.g cloudflare_ip)
```
