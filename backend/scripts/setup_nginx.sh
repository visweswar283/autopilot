#!/bin/bash
# Run this script ON the EC2 instance (via SSH) AFTER:
#   1. You have added an A record: api.applypilotjobs.com → <EC2 public IP>
#   2. DNS has propagated (verify with: nslookup api.applypilotjobs.com)
#
# Usage:
#   ssh -i applypilot-key.pem ec2-user@<EC2_IP>
#   sudo bash setup_nginx.sh

set -e

DOMAIN="api.applypilotjobs.com"
EMAIL="visweswar283@gmail.com"   # Used for Let's Encrypt expiry notices

echo "==> Installing nginx and certbot..."
yum install -y nginx python3-pip
pip3 install certbot certbot-nginx

echo "==> Writing initial nginx config..."
cat > /etc/nginx/conf.d/applypilot.conf <<'NGINX'
server {
    listen 80;
    server_name api.applypilotjobs.com;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;

        # SSE support (for /events/stream)
        proxy_set_header   Connection        '';
        proxy_buffering    off;
        chunked_transfer_encoding on;
    }
}
NGINX

echo "==> Enabling and starting nginx..."
systemctl enable nginx
systemctl restart nginx

echo "==> Obtaining SSL certificate from Let's Encrypt..."
certbot --nginx \
  -d "$DOMAIN" \
  --non-interactive \
  --agree-tos \
  -m "$EMAIL" \
  --redirect

echo "==> Setting up auto-renewal cron..."
echo "0 3 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'" \
  > /etc/cron.d/certbot-renew

echo ""
echo "==> Done! API is now available at https://${DOMAIN}/api/v1"
echo ""
echo "Next: add these GitHub Secrets if not already set:"
echo "  NEXT_PUBLIC_API_URL  = https://${DOMAIN}/api/v1"
echo "  SMTP_HOST            = email-smtp.us-east-1.amazonaws.com"
echo "  SMTP_PORT            = 587"
echo "  SMTP_USER            = <SES SMTP username from AWS console>"
echo "  SMTP_PASS            = <SES SMTP password from AWS console>"
echo "  ALLOWED_ORIGINS      = https://applypilotjobs.com,https://www.applypilotjobs.com"
