from django.shortcuts import render, redirect
from .models import Customer, Account
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .utils import send_otp, pyotp
from datetime import datetime
from django.http import HttpResponseRedirect
from django.urls import reverse


# Customer Login, Signup and logout views


def customer_signup(request):

    if request.method == "POST":
        first_name = request.POST.get("first_name").title()
        last_name = request.POST.get("last_name").title()
        email = request.POST.get("email").lower()
        password = request.POST.get("password")
        password2 = request.POST.get("password2")

        if password != password2:
            error_message = "Passwords don't match. Please try again."
            messages.error(request, error_message)
            return redirect("customer_signup")

        if Customer.objects.filter(email=email).exists():
            error_message = (
                "Email already registered. Please log in or use a different email."
            )
            messages.error(request, error_message)
        else:
            try:
                # Creating Customer
                customer = Customer.objects.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=password,
                )
                customer.is_customer = True
                customer.approved = True
                customer.save()
                success_message = "Please verify your email."
                messages.success(request, success_message)

                # Customer activation
                request.session["email"] = customer.email
                request.session["target_page"] = "customer_login"
                request.session["account_type"] = "customer"
                return redirect("otp_view")

            except Exception as e:

                # Checking if the email is already registered but not as a customer profile
                if Account.objects.filter(email=email).exists():
                    error_message = "Email already registered and not associated with a customer account. Please use a different email."
                    messages.error(request, error_message)
                else:
                    error_message = "Something went wrong, please try again"
                    messages.error(request, error_message)

    title = "Signup"
    context = {"title": title}
    return render(request, "accounts/customer-signup.html", context)



def customer_login(request):

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        try:
            customer = Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            error_message = "Account not found. Please check your email and try again."
            messages.error(request, error_message)
            return redirect("customer_login")

        if not customer.is_active:
            request.session["email"] = email
            request.session["target_page"] = "customer_login"
            request.session["account_type"] = "customer"

            error_message = "Please verify your email to login."
            messages.error(request, error_message)
            return redirect("otp_view")

        authenticated_user = authenticate(email=email, password=password)
        if authenticated_user is None:
            error_message = "Invalid password. Please try again."
            messages.error(request, error_message)
            return redirect("customer_login")

        login(request, authenticated_user)
        target_url = request.session.pop("customer_target_url", reverse("home"))
        return redirect("home")

    title = "LogIn"
    context = {"title": title}
    return render(request, "accounts/customer-login.html", context)


def customer_logout(request):
    logout(request)
    return redirect("home")




# Custom admin Login and logout views


def admin_login(request):

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            account = Account.objects.get(email=email)
            if not account.is_superadmin:
                error_message = "Access denied. Please check your email and password"
                messages.error(request, error_message)
                return redirect("admin_login")
        except Account.DoesNotExist:
            error_message = "Access denied. Please check your email and password"
            messages.error(request, error_message)
            return redirect("admin_login")

        authenticated_user = authenticate(email=email, password=password)
        if authenticated_user is None:
            error_message = "Invalid password. Please try again."
            messages.error(request, error_message)
            return redirect("admin_login")

        login(request, authenticated_user)
        target_url = request.session.pop("admin_target_url", reverse("admin_dashboard"))
        return redirect("admin_dashboard")

    return render(request, "aadmin/admin-login.html")


def admin_logout(request):
    logout(request)
    return redirect("admin_login")


# Account activation views


def otp_view(request):
    send_otp(request)
    return redirect("customer_activation")


def customer_activation(request):
    email = request.session.get("email")
    otp_secret_key = request.session.get("otp_secret_key")
    otp_counter = request.session.get("otp_counter")
    otp_valid_till = datetime.fromisoformat(request.session.get("otp_valid_till"))
    time_left = round((otp_valid_till - datetime.now()).total_seconds())

    if request.method == "POST":
        otp = request.POST.get("otp")

        if otp_secret_key and otp_valid_till is not None:
            if otp_valid_till > datetime.now():
                hotp = pyotp.HOTP(otp_secret_key)
                if hotp.verify(otp, otp_counter):
                    # Activating account
                    account = Account.objects.get(email=email)
                    account.is_active = True
                    account.save()

                    # Deleting OTP cookies from session
                    request.session.pop("otp_secret_key", None)
                    request.session.pop("otp_valid_till", None)
                    request.session.pop("otp_counter", None)

                    success_message = "Your email is verified. Please Login now"
                    messages.success(request, success_message)

                    # redirecting to targeted page
                    target_page = request.session.get("target_page")
                    return redirect(target_page)
                else:
                    error_message = "Invalid OTP"
                    messages.error(request, error_message)
            else:
                error_message = "OTP expired. Click 'Resend OTP' to get a new one."
                messages.error(request, error_message)
        else:
            error_message = "Something went wrong. Please try again."
            messages.error(request, error_message)

    context = {"time_left": time_left}
    account_type = request.session.get("account_type")

   
    if account_type == "customer":
        return render(request, "accounts/customer-activation.html", context)
