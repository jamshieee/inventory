from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, F
from .models import Product, Category, Order, Supplier


# ─────────────────────────── DASHBOARD ───────────────────────────
def dashboard(request):
    total_products = Product.objects.count()
    total_stock = Product.objects.aggregate(total=Sum('stock'))['total'] or 0
    orders_today = Order.objects.filter(order_date__date=__import__('datetime').date.today()).count()
    revenue = Order.objects.filter(status='completed').aggregate(
        total=Sum('total_price')
    )['total'] or 0

    out_of_stock = Product.objects.filter(stock=0)
    low_stock = Product.objects.filter(stock__gt=0, stock__lte=F('low_stock_threshold'))
    highest_sale = (
        Order.objects.values('product__name', 'product__category__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')
        .first()
    )

    context = {
        'total_products': total_products,
        'total_stock': total_stock,
        'orders_today': orders_today,
        'revenue': revenue,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'highest_sale': highest_sale,
        'active': 'dashboard',
    }
    return render(request, 'inventory/dashboard.html', context)


# ─────────────────────────── PRODUCTS ────────────────────────────
def products(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        supplier_id = request.POST.get('supplier')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        threshold = request.POST.get('low_stock_threshold', 5)

        Product.objects.create(
            name=name,
            category_id=category_id,
            supplier_id=supplier_id if supplier_id else None,
            price=price,
            stock=stock,
            low_stock_threshold=threshold,
        )
        messages.success(request, 'Product added successfully!')
        return redirect('products')

    all_products = Product.objects.select_related('category', 'supplier').all()
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()
    context = {
        'products': all_products,
        'categories': categories,
        'suppliers': suppliers,
        'active': 'products',
    }
    return render(request, 'inventory/products.html', context)


def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, 'Product deleted.')
    return redirect('products')


# ─────────────────────────── CATEGORIES ──────────────────────────
def categories(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        Category.objects.create(name=name, description=description)
        messages.success(request, 'Category added successfully!')
        return redirect('categories')

    all_categories = Category.objects.all()
    context = {
        'categories': all_categories,
        'active': 'categories',
    }
    return render(request, 'inventory/categories.html', context)


def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    messages.success(request, 'Category deleted.')
    return redirect('categories')


# ─────────────────────────── ORDERS ──────────────────────────────
def orders(request):
    if request.method == 'POST':
        product_id = request.POST.get('product')
        quantity = request.POST.get('quantity')
        status = request.POST.get('status', 'pending')
        Order.objects.create(product_id=product_id, quantity=quantity, status=status)
        messages.success(request, 'Order placed successfully!')
        return redirect('orders')

    all_orders = Order.objects.select_related('product').all().order_by('-order_date')
    all_products = Product.objects.all()
    context = {
        'orders': all_orders,
        'products': all_products,
        'active': 'orders',
    }
    return render(request, 'inventory/orders.html', context)


def delete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.delete()
    messages.success(request, 'Order deleted.')
    return redirect('orders')


# ─────────────────────────── SUPPLIERS ───────────────────────────
def suppliers(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        Supplier.objects.create(name=name, email=email, phone=phone, address=address)
        messages.success(request, 'Supplier added successfully!')
        return redirect('suppliers')

    all_suppliers = Supplier.objects.all()
    context = {
        'suppliers': all_suppliers,
        'active': 'suppliers',
    }
    return render(request, 'inventory/suppliers.html', context)


def delete_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.delete()
    messages.success(request, 'Supplier deleted.')
    return redirect('suppliers')
