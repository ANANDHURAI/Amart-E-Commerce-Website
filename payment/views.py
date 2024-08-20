from django.shortcuts import render, redirect
import razorpay
from django.conf import settings
from customer.models import Order, Cart, CartItem
from django.urls import reverse
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.views.decorators.csrf import csrf_exempt
from accounts.models import Customer
from django.contrib import messages
from customer.views import create_order
from django.contrib.auth.decorators import login_required


# Customer Payment Session

# RazorPay intergration

# Authorize razorpay client with API Key.

razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET)
)


@login_required
def razorpay_order_creation(request, amount):
    currency = "INR"
    amount = int(amount) * 100

    data = {"amount": amount, "currency": currency, "receipt": str(request.user.id)}
    razorpay_order = razorpay_client.order.create(data)

    razorpay_order_id = razorpay_order["id"]
    current_host = request.get_host()
    callback_url = reverse("razorpay_paymenthandler")
    context = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_merchant_key": settings.RAZOR_KEY_ID,
        "razorpay_amount": amount,
        "actual_amount": amount / 100,
        "currency": currency,
        "callback_url": callback_url,
    }

    return render(request, "customer/customer-payment.html", context=context)


@csrf_exempt
@login_required
def razorpay_paymenthandler(request):
    # Ensure CSRF protection
    if request.method != "POST":
        raise Http404("Invalid Request Method")

    try:
        # Get the required parameters from the POST request
        payment_id = request.POST.get("razorpay_payment_id", "")
        razorpay_order_id = request.POST.get("razorpay_order_id", "")
        signature = request.POST.get("razorpay_signature", "")
        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }

        # Verify the payment signature
        try:
            result = razorpay_client.utility.verify_payment_signature(params_dict)
            if result:
                if "pay_now" in request.session:
                    is_order_updated = pay_now_update(request)
                else:
                    is_order_created = create_order(request)
                return redirect("payment_success")
            else:
                error_message = "Payment Failed. Please try again."
                messages.error(request, error_message)
                return redirect("checkout")
        except Exception as e:
            error_message = "Payment Failed. Please try again."
            messages.error(request, error_message)
            return redirect("checkout")

    except KeyError:
        # Missing required parameters in POST data
        return HttpResponseBadRequest("Missing Parameters")
    except Exception as e:
        # Other exceptions
        error = f"Error processing payment: {str(e)}"
        return HttpResponse(f"Payment Failed {error}", status=500)


@login_required
def cash_on_delivery(request):
    is_order_created = create_order(request)
    if is_order_created:
        return redirect("payment_success")
    else:
        error_message = "Something went wrong. Please try again."
        messages.error(request, error_message)
        return redirect("checkout")


@login_required
def payment_success(request):
    if "address_id" in request.session:
        del request.session["address_id"]
    if "payment_method" in request.session:
        del request.session["payment_method"]
    return render(request, "customer/customer-payment-success.html")

@login_required
def pay_now(request, order_id):
    order = Order.objects.get(id=order_id)
    request.session["pay_now"] = "pay_now"
    request.session["order_id"] = order_id
    return redirect("razorpay_order_creation", amount=order.total_amount)


@login_required
def pay_now_update(request):
    try:
        order_id = request.session.get("order_id")
        order = Order.objects.get(id=order_id)
        order.is_paid = True
        order.payment_method = "razorpay"
        order.save()
        del request.session["pay_now"]
        del request.session["order_id"]
        return True

    except Exception as e:
        return False
    
    