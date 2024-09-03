from django.shortcuts import render, redirect,get_object_or_404
from accounts.models import Customer
from django.http import HttpResponse
from .models import Cart, CartItem, Address, Order, OrderItem, FavouriteItem, Wallet
from aadmin.models import Coupon, CategoryOffer
from product.models import Product, Inventory
from .utils import list_of_states_in_india
from django.db.models import Sum
from django.contrib import messages
from django.contrib.auth import logout
from ecom.views import get_next_url
from django.contrib.auth.decorators import login_required

# def@login_required(func):
#     """
#     Custom login required decorator to check if the user is authenticated and a customer.
#     """

#     def wrapper(request, *args, **kwargs):
#         if not request.user.is_authenticated or not request.user.is_customer:
#             target_url = request.build_absolute_uri()
#             request.session["customer_target_url"] = target_url
#             return redirect("customer_login")
#         return func(request, *args, **kwargs)

#     return wrapper


# Customer Profile Session

@login_required(login_url='customer_login')
def dashboard(request):
    try:
        customer = Customer.objects.get(id=request.user.id)
    except Customer.DoesNotExist:
        customer=None
    orders = (
        Order.objects.filter(
            customer=customer,
        )
        .annotate(total_quantity=Sum("items__quantity"))
        .order_by("-created_at")
    )[:5]

    for order in orders:
        order.order_items = OrderItem.objects.filter(order=order)

    try:
        customer.address = Address.objects.get(customer=customer, is_default=True)
    except:
        pass

    context = {"customer": customer, "orders": orders}
    return render(request, "customer/customer-dashboard.html", context)


@login_required
def address(request):
    customer = Customer.objects.get(id=request.user.id)
    addresses = Address.objects.filter(customer=customer)
    context = {"customer": customer, "addresses": addresses}
    return render(request, "customer/customer-address.html", context)


@login_required
def profile(request):
    customer = Customer.objects.get(id=request.user.id)
    context = {"customer": customer}
    return render(request, "customer/customer-profile.html", context)


@login_required
def edit_profile(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name").title()
        last_name = request.POST.get("last_name").title()
        mobile = request.POST.get("mobile")

        customer = Customer.objects.get(id=request.user.id)
        customer.first_name = first_name
        customer.last_name = last_name
        customer.mobile = mobile
        customer.save()

    return redirect("customer_profile")


@login_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        customer = Customer.objects.get(id=request.user.id)

        if not customer.check_password(current_password):
            error_message = "The current password you entered is incorrect."
            messages.error(request, error_message)
            return redirect("change_password")

        if password1 != password2:
            error_message = "The new passwords do not match. Please try again."
            messages.error(request, error_message)
            return redirect("change_password")

        customer.set_password(password1)
        customer.save()
        logout(request)
        success_message = "Your password has been successfully changed. Please Login"
        messages.success(request, success_message)
        return redirect("customer_profile")

    return render(request, "customer/change-password.html")


@login_required
def new_address(request):
    if request.method == "POST":
        name = request.POST.get("name").title()
        pincode = int(request.POST.get("pincode"))
        mobile = int(request.POST.get("mobile"))
        building = request.POST.get("building").title()
        street = request.POST.get("street").title()
        city = request.POST.get("city").title()
        district = request.POST.get("district").title()
        state = request.POST.get("state").title()
        customer = Customer.objects.get(id=request.user.id)
        address_parts = [
            name,
            building,
            street,
            f"{district}, {state}",
            f"Pincode - {str(pincode)}",
            f"Mobile: {str(mobile)}",
        ]
        if city:
            address_parts.insert(3, city)
        address_text = "\n".join(address_parts)

        if not all([name, pincode, mobile, building, street, district, state]):
            messages.error(request, "Please fill in all required fields.")
            return redirect("new_address")

        new_address = Address.objects.create(
            customer=customer,
            name=name,
            pincode=pincode,
            mobile=mobile,
            building=building,
            street=street,
            city=city,
            district=district,
            state=state,
            address_text=address_text,
        )

        if Address.objects.filter(customer=customer).count() == 1:
            new_address.is_default = True

        if "checkout_submit" in request.POST:
            return redirect("checkout")

        return redirect("customer_address")

    context = {"states": list_of_states_in_india}
    return render(request, "customer/address_form.html", context)


@login_required
def edit_address(request, address_id):
    address = Address.objects.get(id=address_id)
    if request.method == "POST":
        name = request.POST.get("name").title()
        pincode = int(request.POST.get("pincode"))
        mobile = int(request.POST.get("mobile"))
        building = request.POST.get("building").title()
        street = request.POST.get("street").title()
        city = request.POST.get("city").title()
        district = request.POST.get("district").title()
        state = request.POST.get("state").title()
        customer = Customer.objects.get(id=request.user.id)
        address_parts = [
            name,
            building,
            street,
            f"{district}, {state}",
            f"Pincode: {int(pincode)}",
            f"Mobile: {int(mobile)}",
        ]
        if city:
            address_parts.insert(3, city)
        address_text = "\n".join(address_parts)

        address.customer = customer
        address.name = name
        address.pincode = pincode
        address.mobile = mobile
        address.building = building
        address.street = street
        address.city = city
        address.district = district
        address.state = state
        address.address_text = address_text
        address.save()

        return redirect("customer_address")

    context = {"address": address, "states": list_of_states_in_india}
    return render(request, "customer/address_form.html", context)


@login_required
def remove_address(request, address_id):
    address = Address.objects.get(id=address_id)
    address.delete()

    return redirect("customer_address")


@login_required
def default_address(request, address_id):
    address = Address.objects.get(id=address_id)

    try:
        address_default = Address.objects.get(is_default=True)
        address_default.is_default = False
        address_default.save()
    except Exception as e:
        pass

    address.is_default = True
    address.save()

    return redirect("customer_address")


@login_required
def orders(request):
    customer = Customer.objects.get(id=request.user.id)
    orders = (
        Order.objects.filter(customer=customer)
        .annotate(total_quantity=Sum("items__quantity"))
        .order_by("-created_at")
    )

    for order in orders:
        order.order_items = OrderItem.objects.filter(order=order)
        order.sub_total = 0

        for order_item in order.order_items:
            order_item.product.primary_image = order_item.product.product_images.filter(
                priority=1
            ).first()
            order.sub_total += order_item.quantity * order_item.inventory.price

    context = {"customer": customer, "orders": orders}
    return render(request, "customer/customer-orders.html", context)


@login_required
def cancel_order(request, order_id):
    order = Order.objects.get(id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    wallet, created = Wallet.objects.get_or_create(customer__id=request.user.id)

    for order_item in order_items:
        if order_item.status != "cancelled":
            order_item.status = "cancelled"
            order_item.inventory.stock += order_item.quantity
            order_item.inventory.save()
            
    order.status = "cancelled"
    
    return redirect("customer_orders")



@login_required
def cancel_order_item(request, order_item_id):
    order_item = OrderItem.objects.get(id=order_item_id)
    wallet, created = Wallet.objects.get_or_create(customer__id=request.user.id)

    if order_item.status != "cancelled":
        order_item.status = "cancelled"
        if order_item.order.is_paid:
            wallet.balance += order_item.quantity*order_item.inventory.price
        order_item.inventory.stock += order_item.quantity
        order_item.inventory.save()
        order_item.save()
        wallet.save()

    return redirect("customer_orders")


# Customer Favourite Session


@login_required
def favourites(request):
    try:
        customer = Customer.objects.get(id=request.user.id)
    except Customer.DoesNotExist:
        customer = None
    favourite_items = FavouriteItem.objects.filter(customer=customer)

    for favourite_item in favourite_items:
        favourite_item.product.primary_image = (
            favourite_item.product.product_images.filter(priority=1).first()
        )
        available_inventory = favourite_item.product.inventory_sizes.first()
        if available_inventory:
            favourite_item.product.price = available_inventory.price
    context = {"favourite_items": favourite_items, "customer": customer}
    return render(request, "customer/favourites.html", context)


@login_required
def add_to_favourite(request, product_id):
    next_url = get_next_url(request)
    customer = Customer.objects.get(id=request.user.id)
    product = Product.objects.get(id=product_id)
    favourite_item, created = FavouriteItem.objects.get_or_create(
        customer=customer, product=product
    )
    return redirect(next_url)


@login_required
def remove_favourite_item(request, favourite_item_id):
    next_url = get_next_url(request)
    favourite_item = FavouriteItem.objects.get(id=favourite_item_id)
    favourite_item.delete()
    return redirect(next_url)


# Customer Cart Session


@login_required
def cart(request):
    customer = Customer.objects.get(id=request.user.id)
    cart, cart_created = Cart.objects.get_or_create(customer=customer)
    cart_items = CartItem.objects.filter(cart=cart)
    total_amount = 0

    for cart_item in cart_items:
        cart_item.product.primary_image = cart_item.product.product_images.filter(
            priority=1
        ).first()

        total_amount += cart_item.quantity * cart_item.inventory.price

    cart.total_amount = total_amount

    context = {"customer": customer, "cart_items": cart_items, "cart": cart}
    return render(request, "customer/cart.html", context)


@login_required
def add_to_cart(request, product_id):
    if request.method == "POST":
        customer = Customer.objects.get(email=request.user.email)
        product = get_object_or_404(Product, pk=product_id)
        cart, cart_created = Cart.objects.get_or_create(customer=customer)
        quantity = int(request.POST.get("product-quantity"))
        size = request.POST.get("product-size")
        
        try:
            inventory = Inventory.objects.get(product=product, size=size)
        except Inventory.DoesNotExist:
            messages.error(request, "Selected size is not available for this product.")
            return redirect("product_page", slug=product.slug)

        if quantity > inventory.stock:
            error_message = (
                f"Only {inventory.stock} item(s) available in stock for this size."
            )
            messages.error(request, error_message)
            return redirect("product_page", slug=product.slug)

        cart_item, cart_item_created = CartItem.objects.get_or_create(
            cart=cart, product=product, inventory=inventory
        )

        # Removing from the Favourites
        try:
            favourite_item = FavouriteItem.objects.get(
                customer=customer, product=product
            )
            favourite_item.delete()
        except FavouriteItem.DoesNotExist:
            pass

        # Managing the maximum number of products per customer
        if not cart_item_created:
            if cart_item.quantity + quantity > 10:
                cart_item.quantity = 10
            else:
                cart_item.quantity += quantity
            cart_item.save()
        else:
            cart_item.quantity = quantity
            cart_item.save()

    return redirect("cart")


@login_required
def update_cart_item(request, cart_item_id):
    if request.method == "POST":
        cart_item = CartItem.objects.get(id=cart_item_id)
        quantity = int(request.POST.get("product-quantity"))
        size = request.POST.get("product-size")
        inventory = Inventory.objects.get(product=cart_item.product, size=size)

        if quantity > inventory.stock:
            error_message = (
                f"Only {inventory.stock} item(s) available in stock for this size."
            )
            messages.error(request, error_message)
            return redirect("product_page", slug=cart_item.product.slug)

        cart_item.quantity = quantity
        cart_item.inventory = inventory
        cart_item.save()

    return redirect("cart")


@login_required
def remove_cart_item(request, cart_item_id):
    cart_item = CartItem.objects.get(id=cart_item_id)

    cart_item.delete()

    return redirect("cart")


@login_required
def checkout(request):
    customer = Customer.objects.get(id=request.user.id)
    cart, cart_created = Cart.objects.get_or_create(customer=customer)
    cart_items = CartItem.objects.filter(cart=cart)
    total_amount = 0
    total_offer = 0
    selected_address_id = False
    selected_payment_method = False
    if "address_id" in request.session:
        selected_address_id = int(request.session.get("address_id"))
    if "payment_method" in request.session:
        selected_payment_method = request.session.get("payment_method")

    if not cart_items:
        return redirect("cart")

    for cart_item in cart_items:
        cart_item.product.primary_image = cart_item.product.product_images.filter(
            priority=1
        ).first()
        offer = 0
        if CategoryOffer.objects.filter(category=cart_item.product.main_category).exists():
            category_offer = CategoryOffer.objects.get(category=cart_item.product.main_category)
            offer = category_offer.discount

        amount = cart_item.quantity * cart_item.inventory.price
        total_amount += amount
        total_offer += round(amount * offer / 100)

    cart.total_amount = total_amount
    cart.total_offer = total_offer
    cart.remaining_amount = total_amount - total_offer

    addresses = Address.objects.filter(customer=customer)

    context = {
        "customer": customer,
        "cart_items": cart_items,
        "cart": cart,
        "addresses": addresses,
        "states": list_of_states_in_india,
        "selected_address_id":selected_address_id,
        "selected_payment_method":selected_payment_method,
    }
    return render(request, "customer/checkout.html", context)


# Customer Order Session


@login_required
def place_order(request):
    if request.method == "POST":
        address_id = request.POST.get("address_id")
        payment_method = request.POST.get("payment_method")
        request.session["address_id"] = address_id
        request.session["payment_method"] = payment_method
        coupon_code = request.POST.get("coupon_code").upper()

        cart = Cart.objects.get(customer=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        total_amount = 0
        total_offer = 0

        for cart_item in cart_items:
            offer = 0
            if CategoryOffer.objects.filter(category=cart_item.product.main_category).exists():
                category_offer = CategoryOffer.objects.get(category=cart_item.product.main_category)
                offer = category_offer.discount

            amount = cart_item.quantity * cart_item.inventory.price
            total_amount += amount
            total_offer += round(amount * offer / 100)
        

        total_amount -= total_offer


        if coupon_code != "":
            if Coupon.objects.filter(code=coupon_code, is_active=True).exists():
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                if coupon.discount >= total_amount:
                    error_message = "Coupon is not valid for this purchase."
                    messages.error(request, error_message)
                    return redirect("checkout")

                if coupon.quantity < 1:
                    error_message = "Coupon expired"
                    messages.error(request, error_message)
                    return redirect("checkout")

                if coupon.minimum_purchase > total_amount:
                    error_message = f"You should purchase for {coupon.minimum_purchase} to appply this coupon."
                    messages.error(request, error_message)
                    return redirect("checkout")

                total_amount -= coupon.discount
                request.session["discount"] = coupon.discount
                request.session["coupon_code"] = coupon.code
            else:
                error_message = "Invalid Coupon"
                messages.error(request, error_message)
                return redirect("checkout")

        if payment_method == "cod":
            if total_amount > 1000:
                error_message = "COD is not available for orders above 1000 Rs."
                messages.error(request, error_message)
                return redirect("checkout")
            return redirect("cash_on_delivery")
        elif payment_method == "razorpay":
            return redirect("razorpay_order_creation", amount=total_amount)
        else:
            return HttpResponse("PASS")


def create_order(request):
    try:
        address_id = request.session.get("address_id")
        coupon_code = request.session.get("coupon_code")
        discount = request.session.get("discount")
        customer = Customer.objects.get(id=request.user.id)
        address = Address.objects.get(id=address_id)
        cart = Cart.objects.get(customer=customer)
        cart_items = CartItem.objects.filter(cart=cart)
        total_amount = 0
        total_offer = 0

        for cart_item in cart_items:
            offer = 0
            if CategoryOffer.objects.filter(category=cart_item.product.main_category).exists():
                category_offer = CategoryOffer.objects.get(category=cart_item.product.main_category)
                offer = category_offer.discount

            amount = cart_item.quantity * cart_item.inventory.price
            total_amount += amount
            total_offer += round(amount * offer / 100)

        total_amount -= total_offer
        cart.total_amount = total_amount
        cart.total_offer = total_offer

        order = Order.objects.create(
            customer=customer,
            address=address.address_text,
            total_amount=cart.total_amount,
            offer=cart.total_offer,
        )

        if coupon_code:
            coupon = Coupon.objects.get(code=coupon_code)
            order.discount = discount
            order.coupon = coupon
            order.total_amount -= coupon.discount
            order.save()
            coupon.quantity -= 1
            del request.session["discount"]
            del request.session["coupon_code"]
            coupon.save()

        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                inventory=cart_item.inventory,
                quantity=cart_item.quantity,
            )

            cart_item.inventory.stock -= cart_item.quantity
            cart_item.inventory.save()
            cart_item.delete()

        payment_method = request.session["payment_method"]
        if payment_method == "cod":
            order.payment_method = payment_method
            order.is_paid = False
            order.save()

        if payment_method == "razorpay":
            order.payment_method = payment_method
            order.is_paid = True
            order.save()

        del request.session["payment_method"]

        return True
    except Exception as e:
        print(e)
        return False


# Wallet management


@login_required
def customer_wallet(request):
    customer = Customer.objects.get(id=request.user.id)
    wallet, is_wallet_created = Wallet.objects.get_or_create(customer=customer)
    order_items = OrderItem.objects.filter(order__customer=customer, status="cancelled").order_by("-id")

    context = {"customer": customer, "wallet": wallet, "order_items": order_items}
    return render(request, "customer/customer-wallet.html", context)


@login_required
def invoice(request, order_id):
    order = Order.objects.get(id=order_id)
    order.order_items = OrderItem.objects.filter(order=order)
    order.sub_total = 0

    for order_item in order.order_items:
        order_item.product.primary_image = order_item.product.product_images.filter(
            priority=1
        ).first()
        order.sub_total += order_item.quantity * order_item.inventory.price
    
    context = {"order":order}
    return render(request, "customer/invoice.html", context)

