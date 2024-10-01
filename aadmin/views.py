from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import Customer, Account
from product.models import Category, Product, Inventory, ProductImage
from customer.models import OrderItem, Order
from aadmin.models import Coupon, CategoryOffer
from django.utils.text import slugify
from django.contrib import messages
from django.http import HttpResponse
from datetime import datetime, timedelta, date
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q


def admin_login_required(func):
    """
    Custom login required decorator to check if the user is authenticated and a superadmin.
    """

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superadmin:
            target_url = request.build_absolute_uri()
            request.session["admin_target_url"] = target_url
            return redirect("admin_login")
        return func(request, *args, **kwargs)

    return wrapper


@admin_login_required
def admin_dashboard(request):
    title = "Dashboard"
    current_page = "admin_dashboard"

    top_products_info = (
        OrderItem.objects.filter(product__isnull=False)
        .values("product__id", "product__name")
        .annotate(total_quantity=Coalesce(Sum("quantity"), 0))
        .order_by("-total_quantity")[:5]
    )

    top_products = []

    for product_info in top_products_info:
        try:
            product = get_object_or_404(Product, id=product_info["product__id"])
            primary_image = product.product_images.filter(priority=1).first()
            product.primary_image = primary_image
            product.total_quantity = product_info["total_quantity"]
            top_products.append(product)
        except:
            continue

    top_categories_info = (
        Product.objects.filter(main_category__isnull=False)
        .values("main_category__id")
        .annotate(total_quantity=Coalesce(Sum("orderitem__quantity"), 0))
        .order_by("-total_quantity")[:10]
    )

    top_categories = []

    for category_info in top_categories_info:
        try:
            category = get_object_or_404(
                Category, id=category_info["main_category__id"]
            )
            category.total_quantity = category_info["total_quantity"]
            top_categories.append(category)
        except:
            # Log the error or handle it as needed
            continue

    # Line chart for revenue for last year

    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    months = []
    revenue_by_month = []

    current_date = start_date
    while current_date <= end_date:
        month_start_date = current_date.replace(day=1)
        next_month_start_date = (
            current_date.replace(day=1) + timedelta(days=32)
        ).replace(day=1)

        month_label = month_start_date.strftime("%b")

        total_revenue = Order.objects.filter(
            created_at__gte=month_start_date, created_at__lt=next_month_start_date
        ).aggregate(total=Sum("total_amount"))["total"]

        months.append(month_label)
        revenue_by_month.append(total_revenue or 0)

        current_date = next_month_start_date

    total_yearly_revenue = sum(revenue_by_month)

    # Line chart for the month

    today = date.today()
    start_date = today.replace(day=1)
    end_date = today

    days = []
    revenue_by_day = []

    current_date = start_date
    while current_date <= end_date:
        total_revenue = Order.objects.filter(created_at__date=current_date).aggregate(
            total=Sum("total_amount")
        )["total"]

        days.append(current_date.day)
        revenue_by_day.append(total_revenue or 0)

        current_date += timedelta(days=1)

    total_monthly_revenue = sum(revenue_by_day)

    # To count the orders according to the status
    status_counts = {
        "pending": OrderItem.objects.filter(status="pending").count(),
        "confirmed": OrderItem.objects.filter(status="confirmed").count(),
        "shipped": OrderItem.objects.filter(status="shipped").count(),
        "delivered": OrderItem.objects.filter(status="delivered").count(),
        "cancelled": OrderItem.objects.filter(status="cancelled").count(),
    }

    context = {
        "current_page": current_page,
        "title": title,
        "top_products": top_products,
        "top_categories": top_categories,
        "months": months,
        "revenue_by_month": revenue_by_month,
        "days": days,
        "revenue_by_day": revenue_by_day,
        "total_yearly_revenue": total_yearly_revenue,
        "total_monthly_revenue": total_monthly_revenue,
        "status_counts": status_counts,
        "total_orders": OrderItem.objects.all().count(),
    }
    return render(request, "aadmin/admin-dashboard.html", context)


@admin_login_required
def customer_list(request):
    title = "Customers"
    current_page = "customer_list"
    customers = Customer.objects.all()
    request.session["selection"] = "all"

    
    if request.method == "POST":
        filter_option = request.POST.get("filter_option")
        if filter_option == "banned":
            customers = Customer.objects.filter(approved=False)
            request.session["selection"] = "ban"

    context = {"customers": customers, "current_page": current_page, "title": title}
    return render(request, "aadmin/customer-list.html", context=context)


@admin_login_required
def customer_approval(request, pk):
    customer = Customer.objects.get(pk=pk)
    customer.approved = not customer.approved
    customer.save()

    return redirect("customer_list")


@admin_login_required
def category_list(request):
    title = "Categories"
    current_page = "category_list"

    search_query = request.GET.get("search", "")

    if search_query:
        categories = Category.objects.filter(Q(name__icontains=search_query)).order_by(
            "name"
        )
    else:
        categories = Category.objects.all().order_by("name")

    request.session["selection"] = "listed_categories"

    for category in categories:
        category.count = category.main_category_products.count()

    if request.method == "POST":
        filter_option = request.POST.get("filter_option")
        if filter_option == "deleted_categories":
            categories = Category.all_objects.filter(is_deleted=True)
            request.session["selection"] = "deleted_categories"
            for category in categories:
                category.count = Product.all_objects.filter(
                    main_category=category
                ).count()

    paginator = Paginator(categories, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "categories": page_obj,
        "title": title,
        "current_page": current_page,
        "search_query": search_query,
    }
    return render(request, "aadmin/category-list.html", context)


@admin_login_required
def add_category(request):
    title = "New Category"
    current_page = "add_category"

    if request.method == "POST":
        category_name = request.POST.get("category_name").title()
        category_description = request.POST.get("category_description")
        category_image = request.FILES.get("category_image")
        slug = slugify(category_name)

        if "image" not in category_image.content_type:
            error_message = "Please select an image file"
            messages.error(request, error_message)
            return redirect("add_category")

        if Category.objects.filter(name=category_name).exists():
            error_message = "Category already exists"
            messages.error(request, error_message)
            return redirect("add_category")

        # Creating a new category
        new_category = Category.objects.create(
            name=category_name,
            description=category_description,
            image=category_image,
            slug=slug,
        )
        return redirect("category_list")

    context = {"title": title, "current_page": current_page}
    return render(request, "aadmin/category-form.html", context)


@admin_login_required
def edit_category(request, slug):
    title = f"{slug.capitalize()} | Edit Category"
    category = Category.objects.get(slug=slug)
    image_url = category.image.url

    if request.method == "POST":
        category_name = request.POST.get("category_name").title()
        category_description = request.POST.get("category_description")
        category_image = request.FILES.get("category_image")
        new_slug = slugify(category_name)

        if Category.objects.filter(name=category_name).exists():
            error_message = "Category already exists"
            messages.error(request, error_message)
            return redirect("edit_category", slug=slug)

        # Updating the category
        category.name = category_name
        category.description = category_description
        category.slug = new_slug
        if category_image:
            category.image = category_image
        category.save()
        return redirect("category_list")

    context = {"title": title, "category": category, "image_url": image_url}
    return render(request, "aadmin/category-form.html", context)


@admin_login_required
def delete_category(request, slug):
    category = get_object_or_404(Category, slug=slug)

    # Soft deleting products related to the category
    for product in category.main_category_products.all():
        product.delete()
    category.delete()

    return redirect("category_list")


@admin_login_required
def restore_category(request, slug):
    category = Category.all_objects.get(slug=slug)
    products = Product.all_objects.filter(main_category=category)

    for product in products:
        product.restore()

    category.restore()

    return redirect("category_list")


@admin_login_required
def product_list(request):
    title = "Products"
    current_page = "product_list"
    products = Product.objects.all().order_by('-created_at')
    request.session["selection"] = "all"

    # Handle filtering
    if request.method == "POST":
        filter_option = request.POST.get("filter_option")
        if filter_option == "awaiting_listing":
            products = Product.objects.filter(approved=False)
            request.session["selection"] = "awaiting_listing"
        elif filter_option == "listed_products":
            products = Product.objects.filter(approved=True)
            request.session["selection"] = "listed_products"

    # Handle search
    search_query = request.GET.get("search", "")
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | Q(mrp__icontains=search_query)
        )

    paginator = Paginator(products, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for product in page_obj:
        inventory = Inventory.objects.filter(product=product)
        total_stock = sum(inv.stock for inv in inventory)
        product.total_stock = total_stock

    context = {
        "products": page_obj,
        "current_page": current_page,
        "title": title,
        "search_query": search_query,
    }
    return render(request, "aadmin/product-list.html", context=context)


@admin_login_required
def add_product(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        main_category_id = request.POST.get("category")
        images = request.FILES.getlist("images")
        is_available = request.POST.get("is_available")
        approved = request.POST.get("approved")
        print("aveolsnnj:", is_available)
        print("apporverd:", approved)

       
        if not name or not main_category_id:
            messages.error(request, "Name, Main Category is mandatory.")
            return redirect("add_product")
        
        if description and not description.strip():
            messages.error(request, "Description cannot contain only spaces.")
            return redirect("add_product")

        if not name.strip():
            messages.error(request, "Product name cannot contain only spaces.")
            return redirect("add_product")
    
        allowed_image_types = ["image/jpeg", "image/png", "image/gif"]
        for image in images:
            if image.content_type not in allowed_image_types:
                messages.error(
                    request, "Only JPEG, PNG, and GIF formats are supported."
                )
                return redirect("add_product")

       
        main_category = Category.objects.get(id=main_category_id)
        slug = slugify(name)

        product = Product.objects.create(
            name=name,
            description=description,
            main_category=main_category,
            slug=slug,
            is_available=is_available == "on",
            approved=approved == "on",
        )

        
        for i, image in enumerate(images):
            ProductImage.objects.create(product=product, image=image, priority=i + 1)

        messages.success(request, "Product added successfully.")
        return redirect("product_list")

    categories = Category.objects.all()
    context = {"categories": categories}
    return render(request, "aadmin/product-form.html", context)


@admin_login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        main_category_id = request.POST.get("category")
        is_available = request.POST.get("is_available")
        approved = request.POST.get("approved")

        # Validate mandatory fields
        if not name or not main_category_id:
            messages.error(request, "Name and Main Category are mandatory.")
            return redirect("edit_product", product_id=product.id)

        
        allowed_image_types = ["image/jpeg", "image/png", "image/gif"]
        images = request.FILES.getlist("images")
        for image in images:
            if image.content_type not in allowed_image_types:
                messages.error(
                    request,
                    "Only JPEG, PNG, and GIF formats are supported for new images.",
                )
                return redirect("edit_product", product_id=product.id)

        # Update product details
        product.name = name
        product.description = description
        product.main_category = Category.objects.get(id=main_category_id)
        product.slug = slugify(name)
        product.is_available = is_available == "on"
        product.approved = approved == "on"
        product.save()

        
        for i, image in enumerate(images):
            ProductImage.objects.create(product=product, image=image, priority=i + 1)

        messages.success(request, "Product edited successfully.")
        return redirect("product_list")

    elif request.method == "GET":
        categories = Category.objects.all()
        context = {
            "product": product,
            "categories": categories,
        }
        return render(request, "aadmin/product-edit-form.html", context)


def remove_product_image(request, image_id):
    image = get_object_or_404(ProductImage, id=image_id)
    if request.method == "POST":
        image.delete()
        messages.success(request, "Image removed successfully.")
    return redirect("edit_product", product_id=image.product.id)


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect("product_list")


@admin_login_required
def product_approval(request, pk):
    product = Product.objects.get(pk=pk)
    product.approved = not product.approved
    product.save()
    return redirect("product_list")


@admin_login_required
def add_account(request):
    title = "Add account"
    current_page = "add_account"
    context = {"title": title, "current_page": current_page}

    if request.method == "POST":
        first_name = request.POST.get("first_name").title()
        last_name = request.POST.get("last_name").title()
        email = request.POST.get("email").lower()
        password = request.POST.get("password")
        account_type = request.POST.get("account_type")

        if Account.objects.filter(email=email).exists():
            error_message = (
                "Email already registered. Please log in or use a different email."
            )
            messages.error(request, error_message)

        elif account_type == "customer":
            try:
                # Creating customer
                customer = Customer.objects.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=password,
                )
                customer.is_customer = True
                customer.is_active = True
                customer.approved = True
                customer.save()
            except Exception as e:
                error_message = "Something went wrong, please try again"
                messages.error(request, error_message)

    return render(request, "aadmin/add-account.html", context)


@admin_login_required
def order_list(request):
    title = "Orders"
    current_page = "order_list"

    filter_option = request.GET.get("filter_option", "all")
    search_query = request.GET.get("search", "")

    # Filter orders based on search query
    order_items = OrderItem.objects.all().select_related(
        "order", "product", "inventory", "order__customer"
    ).order_by('-id') 

    if search_query:
        order_items = order_items.filter(product__name__icontains=search_query)

    # Filter orders based on status
    if filter_option != "all":
        order_items = order_items.filter(status=filter_option)

    paginator = Paginator(order_items, 5)
    page = request.GET.get("page")

    try:
        order_items = paginator.page(page)
    except PageNotAnInteger:
        order_items = paginator.page(1)
    except EmptyPage:
        order_items = paginator.page(paginator.num_pages)

    context = {
        "order_items": order_items,
        "current_page": current_page,
        "title": title,
        "search_query": search_query,
        "filter_option": filter_option,
    }
    return render(request, "aadmin/order-list.html", context=context)


@admin_login_required
def update_order_status(request, order_item_id):
    if request.method == "POST":
        new_status = request.POST.get("new_status")
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        order_item.status = new_status
        order_item.save()
        messages.success(
            request, f"Status for order item {order_item_id} updated to {new_status}"
        )
    return redirect("order_list")


@admin_login_required
def sales_report(request):
    title = "Sales Report"
    current_page = "sales_report"

    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    request.session["selection"] = "1_month"

    if request.method == "POST":
        filter_option = request.POST.get("filter_option")

        if filter_option == "today":
            start_date = datetime.now() - timedelta(days=1)
            request.session["selection"] = "today"
        elif filter_option == "1_week":
            start_date = datetime.now() - timedelta(days=7)
            request.session["selection"] = "1_week"
        elif filter_option == "1_month":
            start_date = datetime.now() - timedelta(days=30)
            request.session["selection"] = "1_month"
        elif filter_option == "6_months":
            start_date = datetime.now() - timedelta(days=180)
            request.session["selection"] = "6_months"
        elif filter_option == "1_year":
            start_date = datetime.now() - timedelta(days=360)
            request.session["selection"] = "1_year"
        elif "custom_date" in request.POST:

            start_date_str = request.POST.get("start_date")
            end_date_str = request.POST.get("end_date")

            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError:
                messages.error(request, "Invalid date format.")
                return redirect("sales_report")

            if start_date > end_date:
                messages.error(request, "Start date cannot be after end date!")
                return redirect("sales_report")
            if end_date > datetime.now():
                messages.error(request, "End date cannot be in the future!")
                return redirect("sales_report")

            request.session["selection"] = "custom"

    orders = Order.objects.filter(created_at__range=[start_date, end_date]).order_by(
        "-created_at"
    )
    order_items = OrderItem.objects.filter(order__in=orders).annotate(
        order_created_at=F("order__created_at")
    )
    order_items = order_items.order_by("-order_created_at")

    paginator = Paginator(order_items, 10)
    page = request.GET.get("page")
    try:
        order_items_paginated = paginator.page(page)
    except PageNotAnInteger:
        order_items_paginated = paginator.page(1)
    except EmptyPage:
        order_items_paginated = paginator.page(paginator.num_pages)

    overall_amount = sum(item.inventory.price * item.quantity for item in order_items)
    overall_count = order_items.count()

    start_date_str = start_date.strftime("%d-%m-%Y")
    end_date_str = end_date.strftime("%d-%m-%Y")
    pdf_name = f"amart-sales-report-{start_date_str}-{end_date_str}"

    context = {
        "order_items": order_items_paginated,
        "current_page": current_page,
        "title": title,
        "start_date": start_date,
        "end_date": end_date,
        "pdf_name": pdf_name,
        "overall_amount": overall_amount,
        "overall_count": overall_count,
        "paginator": paginator,
        "page_obj": order_items_paginated,
    }

    return render(request, "aadmin/sales-report.html", context=context)


@admin_login_required
def coupon_list(request):
    title = "Coupons"
    current_page = "coupon_list"
    coupons = Coupon.objects.all().order_by("-created_at")
    request.session["selection"] = "all_coupons"

    if request.method == "POST":
        filter_option = request.POST.get("filter_option")
        if filter_option == "active_coupons":
            coupons = Coupon.objects.filter(is_active=True)
            request.session["selection"] = "active_coupons"
        elif filter_option == "inactive_coupons":
            coupons = Coupon.objects.filter(is_active=False)
            request.session["selection"] = "inactive_coupons"
        elif filter_option == "expired_coupons":
            coupons = Coupon.objects.filter(quantity=0)
            request.session["selection"] = "expired_coupons"

    # Pagination
    paginator = Paginator(coupons, 2)  # Show 10 coupons per page
    page = request.GET.get("page")

    try:
        coupons_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        coupons_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        coupons_page = paginator.page(paginator.num_pages)

    context = {
        "title": title,
        "current_page": current_page,
        "coupons": coupons_page,
        "paginator": paginator,
    }
    return render(request, "aadmin/coupon-list.html", context)


@admin_login_required
def add_coupon(request):
    title = "New Coupon"
    current_page = "add_coupon"

    if request.method == "POST":
        coupon_code = request.POST.get("code").upper()
        discount = request.POST.get("discount")
        quantity = request.POST.get("quantity")
        minimum_purchase = request.POST.get("minimum_purchase")
        active = request.POST.get("active")

        if minimum_purchase < discount:
            error_message = (
                "The discount should be less than the minimum purchase limit"
            )
            messages.error(request, error_message)
            return redirect("add_coupon")

        if Coupon.objects.filter(code=coupon_code).exists():
            error_message = "Coupon already exists"
            messages.error(request, error_message)
            return redirect("add_coupon")

        # Creating a new coupon
        new_coupon = Coupon.objects.create(
            code=coupon_code,
            discount=discount,
            quantity=quantity,
            minimum_purchase=minimum_purchase,
            is_active=active,
        )

        return redirect("coupon_list")

    context = {"title": title, "current_page": current_page}
    return render(request, "aadmin/coupon-form.html", context)


@admin_login_required
def edit_coupon(request, id):
    title = "Edit Coupon"
    current_page = "edit_coupon"
    coupon = Coupon.objects.get(id=id)

    if request.method == "POST":
        coupon_code = request.POST.get("code").upper()
        discount = request.POST.get("discount")
        quantity = request.POST.get("quantity")
        minimum_purchase = request.POST.get("minimum_purchase")
        active = request.POST.get("active")

        if minimum_purchase < discount:
            error_message = (
                "The discount should be less than the minimum purchase limit"
            )
            messages.error(request, error_message)
            return redirect("edit_coupon", id=coupon.id)

        if Coupon.objects.filter(code=coupon_code).exclude(id=coupon.id).exists():
            error_message = "Coupon already exists"
            messages.error(request, error_message)
            return redirect("edit_coupon", id=coupon.id)

        # Updating Coupon
        coupon.code = coupon_code
        coupon.discount = discount
        coupon.quantity = quantity
        coupon.minimum_purchase = minimum_purchase
        coupon.is_active = active
        coupon.save()

        return redirect("coupon_list")

    context = {"title": title, "current_page": current_page, "coupon": coupon}
    return render(request, "aadmin/coupon-form.html", context)


@admin_login_required
def delete_coupon(request, id):
    coupon = Coupon.objects.get(id=id)
    coupon.delete()
    return redirect("coupon_list")


@admin_login_required
def offer_list(request):
    title = "Offers"
    current_page = "offer_list"

    offers = CategoryOffer.objects.all().order_by("discount")

    if request.method == "POST":
        filter_option = request.POST.get("filter_option")
        if filter_option == "active_offers":
            offers = offers.filter(is_active=True)
        elif filter_option == "inactive_offers":
            offers = offers.filter(is_active=False)

    search_query = request.GET.get("search", "")
    if search_query:
        offers = offers.filter(
            Q(category__name__icontains=search_query)
            | Q(discount__icontains=search_query)
        )

    paginator = Paginator(offers, 2)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    request.session["selection"] = "all_offers"

    context = {
        "title": title,
        "current_page": current_page,
        "offers": page_obj,
        "search_query": search_query,
    }
    return render(request, "aadmin/offer-list.html", context)


@admin_login_required
def add_offer(request):
    title = "Add Offer"
    current_page = "add_offer"
    categories = Category.objects.all()

    if request.method == "POST":
        category_id = request.POST.get("category_id")
        discount = int(request.POST.get("discount"))
        active = request.POST.get("active")
        category = Category.objects.get(id=category_id)

        if discount > 100 or discount < 1:
            error_message = "Invalid Discount Percentage"
            messages.error(request, error_message)
            return redirect("add_offer")

        if CategoryOffer.objects.filter(category=category).exists():
            error_message = "An offer already exists for this category"
            messages.error(request, error_message)
            return redirect("add_offer")

        # Creating a new offer
        new_offer = CategoryOffer.objects.create(
            category=category,
            discount=discount,
            is_active=active,
        )

        return redirect("offer_list")

    context = {"title": title, "current_page": current_page, "categories": categories}
    return render(request, "aadmin/offer-form.html", context)


@admin_login_required
def edit_offer(request, id):
    title = "Edit Offer"
    current_page = "edit_offer"
    offer = CategoryOffer.objects.get(id=id)
    categories = Category.objects.all()

    if request.method == "POST":
        category_id = request.POST.get("category_id")
        discount = int(request.POST.get("discount"))
        active = request.POST.get("active")
        category = Category.objects.get(id=category_id)

        if discount > 100 or discount < 1:
            error_message = "Invalid Discount Percentage"
            messages.error(request, error_message)
            return redirect("edit_offer", id=offer.id)

        if (
            CategoryOffer.objects.filter(category=category)
            .exclude(id=offer.id)
            .exists()
        ):
            error_message = "An offer already exists for this category"
            messages.error(request, error_message)
            return redirect("edit_offer", id=offer.id)

        # Updating Offer
        offer.category = category
        offer.discount = discount
        offer.is_active = active
        offer.save()

        return redirect("offer_list")

    context = {
        "title": title,
        "current_page": current_page,
        "offer": offer,
        "categories": categories,
    }
    return render(request, "aadmin/offer-form.html", context)


@admin_login_required
def delete_offer(request, id):
    offer = CategoryOffer.objects.get(id=id)
    offer.delete()
    return HttpResponse("Delete Offer")


@admin_login_required
def inventory_list(request):
    # Search functionality
    search_query = request.GET.get("search", "")

    # Filter based on search query
    inventory = Inventory.objects.select_related("product").filter(
        Q(product__name__icontains=search_query) | Q(size__icontains=search_query)
    ).order_by('-id')

    # Pagination
    paginator = Paginator(inventory, 5)  # Show 10 items per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
    }
    return render(request, "aadmin/inventory-list.html", context)


@admin_login_required
def add_edit_inventory(request, inventory_id=None):

    if inventory_id:
        inventory = get_object_or_404(Inventory, pk=inventory_id)
    else:
        inventory = None

    # Handle form submission
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        price = request.POST.get("price")
        size = request.POST.get("size")
        stock = request.POST.get("stock")

        # Validate data
        if not product_id or not price or not size or not stock:
            messages.error(request, "All fields are required.")
        elif int(price) < 1:
            messages.error(request, "Price must be greater than 0.")
        elif int(stock) < 0:
            messages.error(request, "Stock cannot be negative.")
        else:
            product = get_object_or_404(Product, pk=product_id)

            # Check if an inventory with the same product and size already exists (for adding or editing)
            existing_inventory = (
                Inventory.objects.filter(product=product, size=size)
                .exclude(pk=inventory_id)
                .first()
            )

            if existing_inventory:
                # Error if a duplicate product-size combination exists
                messages.error(
                    request,
                    f"An inventory item with size '{size}' already exists for the selected product.",
                )
            else:
                if inventory:
                    # Update existing inventory item
                    inventory.product = product
                    inventory.price = price
                    inventory.size = size
                    inventory.stock = stock
                    inventory.save()
                    messages.success(request, "Inventory item updated successfully.")
                else:
                    # Create a new inventory item
                    Inventory.objects.create(
                        product=product, price=price, size=size, stock=stock
                    )
                    messages.success(
                        request, "New inventory item created successfully."
                    )

                return redirect(
                    "inventory_list"
                )  # Ensure a redirect or HttpResponse is returned

    # Handle GET request or if form submission fails
    products = Product.objects.all()
    sizes = Inventory.SIZE_CHOICES

    context = {"inventory": inventory, "products": products, "sizes": sizes}

    return render(request, "aadmin/inventory-add.html", context)


@admin_login_required
def inventory_status(request, inventory_id):
    inventory_item = get_object_or_404(Inventory, id=inventory_id)
    inventory_item.is_active = not inventory_item.is_active
    inventory_item.save()
    return redirect("inventory_list")


@admin_login_required
def delete_inventory(request, inventory_id):
    inventory_item = get_object_or_404(Inventory, id=inventory_id)
    inventory_item.delete()
    return redirect("inventory_list")
