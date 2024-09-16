from django.shortcuts import render, redirect
import razorpay
from django.conf import settings
from customer.models import Order, Cart, CartItem ,Wallet
from django.urls import reverse
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.views.decorators.csrf import csrf_exempt
from accounts.models import Customer
from django.contrib import messages
from customer.views import create_order
from django.contrib.auth.decorators import login_required
import logging

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




logger = logging.getLogger(__name__)
@csrf_exempt
@login_required
def razorpay_paymenthandler(request):
    if request.method != "POST":
        raise Http404("Invalid Request Method")

    try:
        payment_id = request.POST.get("razorpay_payment_id", "")
        razorpay_order_id = request.POST.get("razorpay_order_id", "")
        signature = request.POST.get("razorpay_signature", "")
        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }

        try:
            result = razorpay_client.utility.verify_payment_signature(params_dict)
            if result:
                request.session['payment_method'] = 'razorpay'
                request.session['payment_successful'] = True
                return redirect('finalize_order')
            else:
                messages.error(request, "Payment verification failed. Please try again.")
                return redirect("checkout")
        except Exception as e:
            logger.error(f"Razorpay verification error: {str(e)}")
            messages.error(request, "Payment verification failed. Please try again.")
            return redirect("checkout")

    except Exception as e:
        logger.error(f"Razorpay payment handler error: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("checkout")


@login_required
def cash_on_delivery(request):
    request.session['payment_method'] = 'cod'
    request.session['payment_successful'] = True
    return redirect('finalize_order')



@login_required
def payment_success(request):
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
        logger.error(f"Error in pay_now_update: {str(e)}")
        return False
    
@login_required
def wallet_recharge_complete(request):
    if request.session.get('payment_successful') and request.session.get('payment_method') == 'razorpay':
        # Get the order details from Razorpay
        razorpay_order_id = request.session.get('razorpay_order_id')
        order = razorpay_client.order.fetch(razorpay_order_id)
        
        amount = order['amount'] / 100  # Convert back to rupees
        customer = request.user.customer
        customer.wallet.balance += amount
        customer.wallet.save()
        
        messages.success(request, f"Successfully added ₹{amount} to your wallet!")
        
        # Clear session variables
        del request.session['payment_successful']
        del request.session['payment_method']
        del request.session['razorpay_order_id']
        
    return redirect('customer_wallet')


@login_required
def razorpay_callback(request):
    if request.method == "GET":
        payment_id = request.GET.get('razorpay_payment_id', '')
        razorpay_order_id = request.GET.get('razorpay_order_id', '')
        signature = request.GET.get('razorpay_signature', '')
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        try:
            razorpay_client.utility.verify_payment_signature(params_dict)
            order = razorpay_client.order.fetch(razorpay_order_id)
            amount = order['amount'] / 100  # Convert back to rupees
            
            customer = request.user.customer
            wallet = Wallet.objects.get(customer=customer)
            wallet.balance += amount
            wallet.save()
            
            messages.success(request, f'Successfully added ₹{amount} to your wallet!')
        except:
            messages.error(request, 'Payment verification failed. Please try again.')
    return redirect('customer_wallet')