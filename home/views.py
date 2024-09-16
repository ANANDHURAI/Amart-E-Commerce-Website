from django.shortcuts import render, redirect
from product.models import Product, Category, ProductImage, Inventory
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import F, Sum, Q
from customer.models import OrderItem, FavouriteItem
from aadmin.models import CategoryOffer


# Create your views here.
def home(request):
    title = "Home"
    products = Product.approved_objects.filter(is_available=True)[:9]
    inventery=Inventory.objects.filter(product__in=products)
    for product in products:
        primary_image = product.product_images.filter(priority=1).first()
        product.primary_image = primary_image
        inventory_item = inventery.filter(product=product).first()
        if inventory_item:
            product.shop_price = inventory_item.price
        else:
            product.shop_price = None
    
    # for product in products:
        # small_size = product.inventory_sizes.get(size="S")
        # small_size_price = small_size.price
        # product.price = small_size_price
        if FavouriteItem.objects.filter(
            customer__id=request.user.id, product=product
        ).exists():
            product.is_favourite = True
        else:
            product.is_favourite = False

    categories = Category.objects.all()[:4]
    context = {"products": products,
                "categories": categories,
                  "title": title,
                  'inventery':inventery}
    return render(request, "home/home.html", context)


def shop(request):
    title = "Shop"
    sort_by = request.session.get("sort_by", "Relevance")
    selected_category = request.session.get("selected_category", "All Categories")
    

    if "search" in request.GET:
        search_term = request.GET.get("search")
        products = (
            Product.approved_objects.filter(
                Q(name__icontains=search_term)
            )
            
        )
    else:
        products = (
            Product.approved_objects.all()
            
        )

    if request.method == "POST":

        selected_category = request.POST.get("selected_category")
        request.session[selected_category] = selected_category
        sort_by = request.POST.get("sort_by")
        request.session[sort_by] = sort_by

        if selected_category != "All Categories":
            category = Category.objects.get(name=selected_category)
            products = (
                Product.approved_objects.filter(main_category=category)
                
            )
        if sort_by == "Price Low to High":
            products = products.order_by("price")
        elif sort_by == "Price High to Low":
            products = products.order_by("-price")
        elif sort_by == "New Arrivals":
            products = products.order_by("-created_at")
        elif sort_by == "aA - zZ":
            products = products.order_by("name")
        elif sort_by == "zZ - aA":
            products = products.order_by("-name")
        elif sort_by == "Popularity":
            products = products.annotate(
                total_quantity_ordered=Sum("orderitem__quantity")
            )
            products = products.order_by("-total_quantity_ordered")

    for product in products:
        product.primary_image = product.product_images.filter(priority=1).first()
        try:
            product.shop_price = Inventory.objects.filter(product=product)[0].price
        except IndexError:
            product.shop_price = 0 

        if FavouriteItem.objects.filter(
            customer__id=request.user.id, product=product
        ).exists():
            product.is_favourite = True
        else:
            product.is_favourite = False

    #products = [product for product in products for _ in range(1)]
    paginator = Paginator(products, 6)
    page = request.GET.get("page")
    paged_products = paginator.get_page(page)

    categories = Category.objects.all()
    
    context = {
        "products": paged_products,
        "categories": categories,
        "title": title,
        "sort_by": sort_by,
        "selected_category": selected_category,
    }
    return render(request, "home/shop.html", context)


def product_page(request, slug):
    product = Product.approved_objects.get(slug=slug)
    title = product
    product_images = ProductImage.objects.filter(product=product).order_by("priority")
    inventory = Inventory.objects.filter(product=product)
    print(product)
    if FavouriteItem.objects.filter(
        customer__id=request.user.id, product=product
    ).exists():
        product.is_favourite = True
    else:
        product.is_favourite = False

    offer = 0
    if CategoryOffer.objects.filter(category=product.main_category).exists():
        category_offer = CategoryOffer.objects.get(category=product.main_category)
        offer = category_offer.discount

    context = {
        "product": product,
        "offer": offer,
        "inventory": inventory,
        "product_images": product_images,
        "title": title,
    }
    return render(request, "home/product-page.html", context)


def test_modal_view(request):
    return render(request, "home/test_modal.html")




