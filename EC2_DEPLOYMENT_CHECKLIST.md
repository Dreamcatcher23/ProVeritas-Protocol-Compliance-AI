# EC2 Deployment Checklist

## ✅ Quick Reference - Do This in Order

### BEFORE YOU START
- [ ] Download PuTTY: https://www.putty.org/
- [ ] Download WinSCP: https://winscp.net/
- [ ] Have AWS Console access ready
- [ ] Have your project folder ready

---

## STEP 1: AWS Console (15 min)
- [ ] Login to AWS Console
- [ ] Go to EC2 Dashboard
- [ ] Click "Launch Instance"
- [ ] Name: `protocolscout-web-server`
- [ ] AMI: Ubuntu 22.04 LTS
- [ ] Instance type: t3.micro
- [ ] Create key pair: `protocolscout-key.ppk`
- [ ] **SAVE THE .ppk FILE!**
- [ ] Security group: Allow ports 22, 80, 5000
- [ ] Storage: 20 GB
- [ ] Click "Launch instance"
- [ ] Wait for instance to start
- [ ] **COPY PUBLIC IP ADDRESS**

---

## STEP 2: Connect via PuTTY (5 min)
- [ ] Open PuTTY
- [ ] Host: YOUR-EC2-PUBLIC-IP
- [ ] Port: 22
- [ ] Connection → SSH → Auth → Browse → Select .ppk file
- [ ] Click "Open"
- [ ] Login as: `ubuntu`
- [ ] You're in!

---

## STEP 3: Install Software (10 min)
Run these commands in PuTTY:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx -y
```

---

## STEP 4: Upload Files (10 min)
- [ ] Open WinSCP
- [ ] Connect to EC2 (same IP, port 22, user: ubuntu, use .ppk file)
- [ ] Create folder: `protocolscout`
- [ ] Upload ALL files from your project folder
- [ ] **IMPORTANT**: Make sure `.env` file is uploaded!

---

## STEP 5: Setup App (10 min)
Run in PuTTY:

```bash
cd /home/ubuntu/protocolscout
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

- [ ] Test in browser: `http://YOUR-IP:5000`
- [ ] If works, press Ctrl+C

---

## STEP 6: Make it Permanent (10 min)

### Create service file:
```bash
sudo nano /etc/systemd/system/protocolscout.service
```

### Paste this (Ctrl+Shift+V in PuTTY):
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

### Save and start:
```bash
# Press Ctrl+X, then Y, then Enter
sudo systemctl daemon-reload
sudo systemctl start protocolscout
sudo systemctl enable protocolscout
sudo systemctl status protocolscout
```

- [ ] Status shows "Active: active (running)"

---

## STEP 7: Test Live URL
- [ ] Open browser: `http://YOUR-EC2-IP:5000`
- [ ] Register account
- [ ] Login
- [ ] Upload protocol
- [ ] View results
- [ ] Download PDF

---

## ✅ DONE!

**Your live URL**: `http://YOUR-EC2-IP:5000`

Share this URL with judges!

---

## 🆘 If Something Goes Wrong

### Check logs:
```bash
sudo journalctl -u protocolscout -n 50
```

### Restart app:
```bash
sudo systemctl restart protocolscout
```

### Check if .env file exists:
```bash
cat /home/ubuntu/protocolscout/.env
```

---

## 💰 Cost

**Running**: ₹7.50/day  
**Stopped**: ₹2/month (storage only)

To stop: EC2 Console → Select instance → Instance State → Stop

---

## 📝 Your Details

Fill this in:

- **EC2 Public IP**: ___________________
- **Live URL**: http://___________________:5000
- **Key Pair File**: protocolscout-key.ppk (saved at: ___________________)
- **Deployment Date**: ___________________

---

**Total Time**: 45-60 minutes  
**Difficulty**: Medium  
**Result**: Live, working demo URL! 🎉
