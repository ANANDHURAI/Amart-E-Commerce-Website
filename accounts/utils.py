import pyotp, random
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import send_mail
from . models import Account

def send_otp(request):
    otp_counter = random.randint(0, 999999)  # creating a random counter
    secret_key = pyotp.random_base32()
    hotp = pyotp.HOTP(secret_key)
    otp = hotp.at(otp_counter)
    request.session["otp_secret_key"] = secret_key
    request.session["otp_counter"] = otp_counter
    valid_time = datetime.now() + timedelta(seconds=60)
    request.session["otp_valid_till"] = valid_time.isoformat()

    # Sending verification email
    email = request.session.get("email")
    account = Account.objects.get(email=email)
    name = account.first_name + " " + account.last_name
    subject = "OTP Verification - mulberry Fashions"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]
    message = f"""
Dear {name},

Welcome to Amart Fashions! We're thrilled to have you as part of our community.

To complete your registration and unlock all the exciting features, we need to verify your email address. Please use the OTP (One-Time Password) provided below:

OTP: {otp}

Please enter this OTP on the verification page to finalize your registration. If you didn't request this OTP, please disregard this email.

We're here to make your fashion journey extraordinary. If you have any questions or need assistance, feel free to reach out to our support team.


Best regards,
The Amart Fashions Team

[Note: This is an automated email. Please do not reply.]"""
    
    send_mail(subject=subject, message=message, from_email=from_email, recipient_list=recipient_list)