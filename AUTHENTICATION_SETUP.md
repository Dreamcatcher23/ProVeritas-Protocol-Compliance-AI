# ProtocolScout Authentication Setup Guide

This guide explains how to set up and use the user authentication system in ProtocolScout.

## Overview

The authentication system provides:
- User registration with email and password
- Secure login/logout functionality
- Password hashing with bcrypt
- Session management with Flask-Login
- User data storage in DynamoDB
- Protected routes requiring authentication

## Prerequisites

1. AWS account with DynamoDB access
2. AWS credentials configured in `.env` file
3. Python dependencies installed (`pip install -r requirements.txt`)

## Setup Steps

### 1. Create DynamoDB Users Table

Run the setup script to create the `users` table in DynamoDB:

```bash
python create_users_table.py
```

This will create a table with:
- **Table Name**: `users`
- **Primary Key**: `email` (String)
- **Billing Mode**: PAY_PER_REQUEST (on-demand)
- **Attributes**: email, name, institution, password_hash, created_at

### 2. Configure Secret Key

Generate a secure secret key for Flask sessions:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Update your `.env` file with the generated key:

```
SECRET_KEY=your-generated-secret-key-here
```

### 3. Verify Configuration

Check that your `.env` file has all required settings:

```
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
DOCUMENTS_BUCKET=protocolscout-documents
SECRET_KEY=your-generated-secret-key
```

## User Flow

### Registration
1. User visits `/register`
2. Fills in: name, email, institution, password
3. Password is hashed with bcrypt
4. User data stored in DynamoDB `users` table
5. User automatically logged in and redirected to dashboard

### Login
1. User visits `/login`
2. Enters email and password
3. Password verified against stored hash
4. Session created with Flask-Login
5. Redirected to dashboard or requested page

### Logout
1. User clicks logout in navigation
2. Session cleared
3. Redirected to home page

## Protected Routes

The following routes require authentication:
- `/upload` - Upload protocol page
- `/dashboard` - User dashboard
- `/results/<protocol_id>` - View results

Unauthenticated users are redirected to `/login` with a message.

## Navigation Changes

The navigation bar now shows different options based on authentication status:

**Logged Out:**
- Home
- About
- Login
- Register

**Logged In:**
- Home
- Upload Protocol
- Dashboard
- About
- User dropdown (with name and logout option)

## User Data Structure

Each user in DynamoDB has:
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "institution": "Research Hospital",
  "password_hash": "bcrypt-hashed-password",
  "created_at": "2026-03-09T12:00:00"
}
```

## Security Features

1. **Password Hashing**: Passwords are hashed with bcrypt (never stored in plain text)
2. **Session Management**: Flask-Login handles secure session cookies
3. **CSRF Protection**: Flask's built-in CSRF protection
4. **Password Requirements**: Minimum 8 characters
5. **Secure Cookies**: Session cookies are HTTP-only

## Testing the System

### 1. Create a Test User

Visit `http://localhost:5000/register` and create an account:
- Name: Test User
- Email: test@example.com
- Institution: Test Hospital
- Password: testpass123

### 2. Test Login

1. Logout if logged in
2. Visit `http://localhost:5000/login`
3. Enter credentials
4. Verify redirect to dashboard

### 3. Test Protected Routes

1. Logout
2. Try to access `/upload` directly
3. Should redirect to login page
4. Login and verify access granted

## Troubleshooting

### "Unable to locate credentials" Error
- Check AWS credentials in `.env` file
- Verify `load_dotenv()` is called in `app.py`

### "Table does not exist" Error
- Run `python create_users_table.py`
- Verify table created in AWS Console

### "Invalid email or password" Error
- Check email is correct
- Verify password matches registration
- Check DynamoDB table has user record

### Session Not Persisting
- Verify SECRET_KEY is set in `.env`
- Check browser allows cookies
- Restart Flask application

## Production Considerations

For production deployment:

1. **Use Strong Secret Key**: Generate with `secrets.token_hex(32)`
2. **Enable HTTPS**: Required for secure cookies
3. **Set Secure Cookie Flags**: Add to app.py:
   ```python
   app.config['SESSION_COOKIE_SECURE'] = True
   app.config['SESSION_COOKIE_HTTPONLY'] = True
   app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
   ```
4. **Add Rate Limiting**: Prevent brute force attacks
5. **Add Email Verification**: Verify user email addresses
6. **Add Password Reset**: Allow users to reset forgotten passwords
7. **Add 2FA**: Two-factor authentication for extra security

## API Changes

### Upload Endpoint
Now uses authenticated user data:
- `user_id`: Automatically set to `current_user.email`
- `institution`: Automatically set to `current_user.institution`
- No need to pass these in the form

### Dashboard Endpoint
Now shows protocols for logged-in user:
- `user_id`: Automatically set to `current_user.email`
- Queries DynamoDB for user's protocols only

## File Changes Summary

### New Files
- `templates/login.html` - Login page
- `templates/register.html` - Registration page
- `create_users_table.py` - DynamoDB table setup script
- `AUTHENTICATION_SETUP.md` - This guide

### Modified Files
- `app.py` - Added authentication routes and User model
- `templates/base.html` - Updated navigation with auth status
- `templates/index.html` - Updated CTAs based on auth status
- `templates/upload.html` - Removed manual user fields
- `requirements.txt` - Added Flask-Login and bcrypt
- `.env.example` - Added SECRET_KEY note

## Support

For issues or questions:
1. Check this guide
2. Review error messages in console
3. Check AWS CloudWatch logs
4. Verify DynamoDB table structure
