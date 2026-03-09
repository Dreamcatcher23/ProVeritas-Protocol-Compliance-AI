# Quick Start: Authentication System

## 🚀 Get Started in 3 Steps

### Step 1: Generate Secret Key
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and update your `.env` file:
```env
SECRET_KEY=paste-your-generated-key-here
```

### Step 2: Verify Users Table (Already Created ✅)
The `users` table has been created in DynamoDB. You're all set!

### Step 3: Start the Application
```bash
python app.py
```

Visit: `http://localhost:5000`

---

## 🎯 First Time User Flow

1. **Visit Home Page** → Click "Get Started Free"
2. **Register Account** → Fill in name, email, institution, password
3. **Auto Login** → Redirected to dashboard
4. **Upload Protocol** → Click "Upload Protocol" in navigation
5. **View Results** → Check dashboard for your protocols

---

## 🔐 What Changed?

### Before (No Auth)
- Anyone could upload
- Manual user_id entry
- No user tracking
- No session management

### After (With Auth)
- ✅ Secure login required
- ✅ Automatic user tracking
- ✅ Personal dashboard
- ✅ Password protection
- ✅ Session management

---

## 📋 Quick Test

### Test Registration
```
URL: http://localhost:5000/register
Name: Test User
Email: test@example.com
Institution: Test Hospital
Password: testpass123
```

### Test Login
```
URL: http://localhost:5000/login
Email: test@example.com
Password: testpass123
```

### Test Protected Route
1. Logout
2. Try to access: `http://localhost:5000/upload`
3. Should redirect to login ✅

---

## 🛠️ Troubleshooting

### "Unable to locate credentials"
→ Check `.env` file has AWS credentials

### "Table does not exist"
→ Run: `python create_users_table.py`

### "Invalid email or password"
→ Check email/password are correct
→ Try registering a new account

### Session not persisting
→ Verify SECRET_KEY is set in `.env`
→ Restart Flask application

---

## 📁 New Files

- `templates/login.html` - Login page
- `templates/register.html` - Registration page
- `create_users_table.py` - Table setup script
- `AUTHENTICATION_SETUP.md` - Detailed guide
- `AUTHENTICATION_IMPLEMENTATION_SUMMARY.md` - Implementation details

---

## 🎨 UI Changes

### Navigation Bar
**Logged Out:**
- Home | About | Login | Register

**Logged In:**
- Home | Upload Protocol | Dashboard | About | [User Name ▼]
  - My Dashboard
  - Logout

### Home Page
**Logged Out:**
- "Get Started Free" button
- "Sign In" button

**Logged In:**
- "Upload Protocol Now" button

### Upload Page
**Before:** Manual user_id and institution fields
**After:** Shows logged-in user info automatically

---

## 🔒 Security Features

✅ Password hashing with bcrypt
✅ Secure session cookies
✅ Protected routes
✅ CSRF protection
✅ Minimum password length (8 chars)
✅ Flash messages for errors

---

## 📊 Database

**Table:** `users`
**Primary Key:** email
**Attributes:** email, name, institution, password_hash, created_at
**Region:** ap-south-1
**Billing:** PAY_PER_REQUEST

---

## 🎓 Learn More

- **Setup Guide:** `AUTHENTICATION_SETUP.md`
- **Implementation Details:** `AUTHENTICATION_IMPLEMENTATION_SUMMARY.md`
- **Main README:** `README.md`

---

## ✅ You're Ready!

The authentication system is fully implemented and ready to use. Just:
1. Update SECRET_KEY in `.env`
2. Restart the application
3. Register your first account
4. Start uploading protocols!

**Happy Protocol Checking! 🚀**
