# Cloud Infrastructure Guide — VPC, Subnets, Firewall, SSL

## VPC Architecture

```
VPC: 10.0.0.0/16
├── Public Subnet:  10.0.1.0/24  (Nginx, app VM — has Internet Gateway)
└── Private Subnet: 10.0.2.0/24  (DB, internal services — no direct internet)
```

For a single-VM setup (this project), everything runs in one public subnet
behind Docker's internal networks. The `backend` Docker network emulates
the private subnet isolation.

## AWS Setup

### VPC & Subnet
1. VPC → Create VPC → IPv4 CIDR: `10.0.0.0/16`
2. Subnets → Create subnet in your VPC → `10.0.1.0/24`
3. Internet Gateway → Attach to VPC
4. Route Table → Add route `0.0.0.0/0 → igw-xxxxxxxx`

### EC2 Instance
- AMI: Ubuntu 22.04 LTS
- Type: `t3.small` (2 vCPU, 2GB RAM) minimum; `t3.medium` recommended
- Storage: 20GB gp3 SSD
- Enable Auto-assign public IP

## GCP Setup

### VPC Network
```bash
gcloud compute networks create prod-vpc --subnet-mode=custom
gcloud compute networks subnets create prod-subnet \
  --network=prod-vpc --range=10.0.1.0/24 --region=us-central1
```

### VM Instance
```bash
gcloud compute instances create prod-vm \
  --machine-type=e2-small \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --subnet=prod-subnet \
  --boot-disk-size=20GB
```

## Domain DNS Setup

Point your domain's A record to the VM's public IP:
```
A     @              → YOUR_VM_IP
A     www            → YOUR_VM_IP
```
Wait for DNS propagation (2-15 min). Verify:
```bash
dig +short yourdomain.com
```

## SSL Certificate Renewal

Certbot container auto-renews every 12h.
Manual renewal:
```bash
docker compose -f docker-compose.prod.yml run --rm certbot renew
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```
