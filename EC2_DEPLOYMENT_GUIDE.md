# ProtocolScout - Complete EC2 Deployment Guide

## 🎯 Overview
This guide will help you deploy ProtocolScout Flask application on AWS EC2 with a public URL.

**Estimated Time**: 45-60 minutes  
**Cost**: ~₹290 for 2 weeks (t3.micro instance)

---

## 📋 Prerequisites

- AWS Account with EC2 access
- Your AWS credentials (already in .env file)
- PuTTY (for Windows SSH) - Download from: https://www.putty.org/
- WinSCP (for file transfer) - Download from: https://winscp.net/

---

## 🚀 PART 1: Launch EC2 Instance (15 minutes)

### Step 1: Go to AWS Console
1. Open browser: https://console.aws.amazon.com/
2. Login with your AWS account
3. Select region: **Asia Pacific (Mumbai) ap-south-1**

### Step 2: Launch EC2 Instance
1. Go to **EC2 Dashboard**
2. Click **"Launch Instance"** button

### Step 3: Configure Instance

**Name and Tags:**
- Name: `protocolscout-web-server`

**Application and OS Images (AMI):**
- Select: **Ubuntu Server 22.04 LTS (HVM), SSD Volume Type**
- Architecture: **64-bit (x86)**

**Instance Type:**
- Select: **t3.micro** (2 vCPU, 1 GB RAM)
- Cost: ~₹0.0104/hour = ~₹7.50/day

**Key Pair (login):**
- Click **"Create new key pair"**
- Key pair name: `protocolscout-key`
- Key pair type: **RSA**
- Private key file format: **`.ppk`** (for PuTTY on Windows)
- Click **"Create key pair"**
- **IMPORTANT**: Save the `.ppk` file - you'll need it to connect!

**Network Settings:**
- Click **"Edit"**
- Auto-assign public IP: **Enable**
- Firewall (security groups): **Create security group**
- Security group name: `protocolscout-sg`
- Description: `Security group for ProtocolScout web app`

**Add Security Group Rules:**
1. **SSH** (already added)
   - Type: SSH
   - Port: 22
   - Source: My IP (or Anywhere 0.0.0.0/0)

2. **HTTP** (click "Add security group rule")
   - Type: HTTP
   - Port: 80
   - Source: Anywhere 0.0.0.0/0

3. **Custom TCP** (click "Add security group rule")
   - Type: Custom TCP
   - Port: 5000
   - Source: Anywhere 0.0.0.0/0

**Configure Storage:**
- Size: **20 GB** (default 8 GB is too small)
- Volume type: **gp3**

**Advanced Details:**
- Leave as default

### Step 4: Launch
1. Review all settings
2. Click **"Launch instance"**
3. Wait 2-3 minutes for instance to start
4. Click **"View Instances"**

### Step 5: Note Your Instance Details
Once instance is running, note down:
- **Public IPv4 address**: (e.g., 13.232.xxx.xxx)
- **Public IPv4 DNS**: (e.g., ec2-13-232-xxx-xxx.ap-south-1.compute.amazonaws.com)

**Your public URL will be**: `http://YOUR-PUBLIC-IP:5000`

---

## 🔌 PART 2: Connect to EC2 (10 minutes)

### Step 1: Open PuTTY
1. Launch PuTTY application
2. In **"Host Name (or IP address)"**: Enter your EC2 public IP
3. Port: **22**
4. Connection type: **SSH**

### Step 2: Configure SSH Key
1. In left panel, go to: **Connection → SSH → Auth → Credentials**
2. Click **"Browse"** next to "Private key file for authentication"
3. Select your `protocolscout-key.ppk` file
4. Click **"Open"**

### Step 3: Login
1. PuTTY will ask: "login as:"
2. Type: `ubuntu` and press Enter
3. You should see: `Welcome to Ubuntu 22.04...`

**You're now connected to your EC2 instance!**

---

## 📦 PART 3: Install Dependencies (10 minutes)

Copy and paste these commands one by one in PuTTY:

### Step 1: Update System
```bash
sudo apt update && sudo apt upgrade -y
```
(This takes 2-3 minutes)

### Step 2: Install Python and Pip
```bash
sudo apt install python3-pip python3-venv -y
```

### Step 3: Install Nginx (Web Server)
```bash
sudo apt install nginx -y
```

### Step 4: Verify Installations
```bash
python3 --version
pip3 --version
nginx -v
```

You should see version numbers for all three.

---

## 📁 PART 4: Upload Your Code (10 minutes)

### Option A: Using WinSCP (Recommended for Windows)

1. **Open WinSCP**
2. **New Session**:
   - File protocol: **SFTP**
   - Host name: Your EC2 public IP
   - Port: **22**
   - User name: **ubuntu**
3. **Advanced → SSH → Authentication**:
   - Private key file: Select your `protocolscout-key.ppk`
4. Click **"Login"**
5. **Upload files**:
   - Left panel: Navigate to `C:\Users\Dhanvantari\Downloads\AI BHARAT FINAL 9 March`
   - Right panel: You're in `/home/ubuntu/`
   - Create folder: `protocolscout`
   - Drag and drop ALL files from left to right into `protocolscout` folder

**Files to upload:**
- `app.py`
- `requirements.txt`
- `.env` (IMPORTANT!)
- `templates/` folder (all HTML files)
- All other Python files

### Option B: Using Git (Alternative)

If you've pushed to GitHub:
```bash
cd /home/ubuntu
git clone https://github.com/YOUR-USERNAME/protocolscout.git
cd protocolscout
```

Then manually create `.env` file:
```bash
nano .env
```
Paste your environment variables, then Ctrl+X, Y, Enter to save.

---

## ⚙️ PART 5: Setup Application (10 minutes)

### Step 1: Navigate to Project
```bash
cd /home/ubuntu/protocolscout
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your prompt.

### Step 3: Install Python Packages
```bash
pip install -r requirements.txt
```
(This takes 2-3 minutes)

### Step 4: Test Flask App
```bash
python3 app.py
```

You should see:
```
* Running on http://0.0.0.0:5000
```

**Test in browser**: `http://YOUR-EC2-PUBLIC-IP:5000`

If it works, press **Ctrl+C** to stop the server.

---

## 🔧 PART 6: Setup Gunicorn + Systemd (15 minutes)

### Step 1: Install Gunicorn
```bash
pip install gunicorn
```

### Step 2: Test Gunicorn
```bash
gunicorn --bind 0.0.0.0:5000 app:app
```

Test in browser again. If works, press Ctrl+C.

### Step 3: Create Systemd Service File
```bash
sudo nano /etc/systemd/system/protocolscout.service
```

Paste this content:
```ini
[Unit]
Description=ProtocolScout Flask Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/protocolscout
Environment="PATH=/home/ubuntu/protocolscout/venv/bin"
ExecStart=/home/ubuntu/protocolscout/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Save: **Ctrl+X**, then **Y**, then **Enter**

### Step 4: Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl start protocolscout
sudo systemctl enable protocolscout
```

### Step 5: Check Status
```bash
sudo systemctl status protocolscout
```

You should see: **Active: active (running)**

Press **Q** to exit.

---

## 🌐 PART 7: Configure Nginx (Optional - for port 80)

If you want to access without `:5000` in URL:

### Step 1: Create Nginx Config
```bash
sudo nano /etc/nginx/sites-available/protocolscout
```

Paste:
```nginx
server {
    listen 80;
    server_name YOUR-EC2-PUBLIC-IP;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Replace `YOUR-EC2-PUBLIC-IP` with your actual IP.

Save: Ctrl+X, Y, Enter

### Step 2: Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/protocolscout /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Now access: `http://YOUR-EC2-PUBLIC-IP` (without :5000)

---

## ✅ PART 8: Verify Deployment

### Test Your Live URL

1. **Open browser**: `http://YOUR-EC2-PUBLIC-IP:5000`
2. **Register** a new account
3. **Login**
4. **Upload** a protocol PDF
5. **View** results
6. **Download** PDF report

### Check Logs (if issues)
```bash
sudo journalctl -u protocolscout -f
```

Press Ctrl+C to exit.

---

## 🎉 SUCCESS!

Your ProtocolScout app is now live at:
- **URL**: `http://YOUR-EC2-PUBLIC-IP:5000`
- **Status**: Running 24/7
- **Auto-restart**: Enabled (survives reboots)

---

## 📝 Important Commands

### Restart Application
```bash
sudo systemctl restart protocolscout
```

### View Logs
```bash
sudo journalctl -u protocolscout -n 50
```

### Stop Application
```bash
sudo systemctl stop protocolscout
```

### Update Code
```bash
cd /home/ubuntu/protocolscout
# Upload new files via WinSCP
sudo systemctl restart protocolscout
```

---

## 💰 Cost Management

### Current Cost
- **t3.micro**: ₹0.0104/hour = ₹7.50/day = ₹225/month

### Stop Instance (when not needed)
1. Go to EC2 Console
2. Select instance
3. **Instance State → Stop**
4. **Cost while stopped**: Only storage (~₹2/month)

### Start Instance Again
1. Select instance
2. **Instance State → Start**
3. **Note**: Public IP will change!

---

## 🔒 Security Best Practices

### 1. Restrict SSH Access
In Security Group, change SSH source from `0.0.0.0/0` to **"My IP"**

### 2. Setup HTTPS (Optional)
Use Let's Encrypt for free SSL certificate

### 3. Regular Updates
```bash
sudo apt update && sudo apt upgrade -y
```

---

## 🐛 Troubleshooting

### App Not Starting
```bash
sudo systemctl status protocolscout
sudo journalctl -u protocolscout -n 100
```

### Port 5000 Not Accessible
Check security group has port 5000 open

### AWS Credentials Error
Check `.env` file exists:
```bash
cat /home/ubuntu/protocolscout/.env
```

### Out of Memory
Upgrade to t3.small (2GB RAM)

---

## 📞 Support

If you face issues:
1. Check logs: `sudo journalctl -u protocolscout -f`
2. Verify .env file has correct AWS credentials
3. Check security group rules
4. Ensure all files uploaded correctly

---

## 🎯 Next Steps

1. ✅ Deploy to EC2 (you just did this!)
2. ⬜ Push code to GitHub
3. ⬜ Create demo video
4. ⬜ Create presentation PPT

---

**Congratulations! Your ProtocolScout app is now live on AWS EC2!** 🚀
