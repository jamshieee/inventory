from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, F
from decimal import Decimal
from .models import Product, Category, Order, Supplier
import datetime


# ─────────────────────────── DASHBOARD ───────────────────────────
def dashboard(request):
    total_products = Product.objects.count()
    total_stock = Product.objects.aggregate(total=Sum('stock'))['total'] or 0
    orders_today = Order.objects.filter(order_date__date=datetime.date.today()).count()
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

    # ✅ Stock notifications
    out_of_stock_products = Product.objects.filter(stock=0)
    low_stock_products = Product.objects.filter(stock__gt=0, stock__lte=F('low_stock_threshold'))

    for p in out_of_stock_products:
        messages.error(request, f'🚨 OUT OF STOCK: "{p.name}" has 0 units left!')
    for p in low_stock_products:
        messages.warning(request, f'⚠️ LOW STOCK: "{p.name}" has only {p.stock} units left!')

    context = {
        'products': all_products,
        'categories': categories,
        'suppliers': suppliers,
        'active': 'products',
    }
    return render(request, 'inventory/products.html', context)


# ✅ NEW — Edit Product (Stock Replenishment + Full Edit)
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        old_stock = product.stock

        product.name = request.POST.get('name')
        product.category_id = request.POST.get('category')
        product.supplier_id = request.POST.get('supplier') or None
        product.price = request.POST.get('price')
        product.low_stock_threshold = request.POST.get('low_stock_threshold', 5)

        # ✅ Stock replenishment logic
        new_stock = int(request.POST.get('stock', old_stock))
        added_stock = new_stock - old_stock

        product.stock = new_stock
        product.save()

        # ✅ Notify how much stock was added
        if added_stock > 0:
            messages.success(request, f'✅ Stock replenished! {added_stock} units added to "{product.name}". New stock: {product.stock}')
        elif added_stock < 0:
            messages.warning(request, f'⚠️ Stock reduced by {abs(added_stock)} units for "{product.name}". New stock: {product.stock}')
        else:
            messages.success(request, f'✅ Product "{product.name}" updated successfully!')

        return redirect('products')

    categories = Category.objects.all()
    suppliers = Supplier.objects.all()
    context = {
        'product': product,
        'categories': categories,
        'suppliers': suppliers,
        'active': 'products',
    }
    return render(request, 'inventory/edit_product.html', context)


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
# ─────────────────────────── ORDERS ──────────────────────────────
def orders(request):
    if request.method == 'POST':
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity'))
        status = request.POST.get('status', 'pending')

        product = get_object_or_404(Product, pk=product_id)

        # ✅ Check stock before placing completed order
        if status == 'completed':
            if product.stock <= 0:
                messages.error(request, f'🚨 Cannot place order! "{product.name}" is OUT OF STOCK!')
                return redirect('orders')
            if quantity > product.stock:
                messages.error(request, f'🚨 Only {product.stock} units available for "{product.name}"!')
                return redirect('orders')

        # ✅ Create order
        order = Order(product=product, quantity=quantity, status=status)
        order.save()

        # ✅ Notify after order
        if status == 'completed':
            product.refresh_from_db()
            messages.success(request, f'✅ Order placed! "{product.name}" stock now: {product.stock} units.')
            if product.stock == 0:
                messages.error(request, f'🚨 "{product.name}" is now OUT OF STOCK!')
            elif product.stock <= product.low_stock_threshold:
                messages.warning(request, f'⚠️ "{product.name}" is LOW on stock! Only {product.stock} units left.')
        else:
            messages.success(request, '✅ Order placed as Pending.')

        return redirect('orders')

    all_orders = Order.objects.select_related('product').all().order_by('-order_date')
    all_products = Product.objects.all()
    context = {
        'orders': all_orders,
        'products': all_products,
        'active': 'orders',
    }
    return render(request, 'inventory/orders.html', context)


def edit_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        old_status = order.status
        product = order.product

        # ✅ Same status — no change needed
        if old_status == new_status:
            messages.info(request, 'No changes made.')
            return redirect('orders')

        # ✅ Pending → Completed: deduct stock
        if old_status == 'pending' and new_status == 'completed':
            if product.stock <= 0:
                messages.error(request, f'🚨 Cannot complete! "{product.name}" is OUT OF STOCK!')
                return redirect('orders')
            if order.quantity > product.stock:
                messages.error(request, f'🚨 Only {product.stock} units available for "{product.name}"!')
                return redirect('orders')
            product.stock -= order.quantity
            product.save()
            messages.success(request, f'✅ Order completed! Stock reduced. "{product.name}" now has {product.stock} units.')

        # ✅ Completed → Pending: restore stock
        elif old_status == 'completed' and new_status == 'pending':
            product.stock += order.quantity
            product.save()
            messages.success(request, f'✅ Order moved to Pending. {order.quantity} units restored to "{product.name}".')

        # ✅ Completed → Cancelled: restore stock
        elif old_status == 'completed' and new_status == 'cancelled':
            product.stock += order.quantity
            product.save()
            messages.success(request, f'✅ Order cancelled. {order.quantity} units restored to "{product.name}".')

        # ✅ Pending → Cancelled: no stock change
        elif old_status == 'pending' and new_status == 'cancelled':
            messages.success(request, f'✅ Order cancelled.')

        # ✅ Cancelled → Pending: no stock change
        elif old_status == 'cancelled' and new_status == 'pending':
            messages.success(request, f'✅ Order moved back to Pending.')

        # ✅ Cancelled → Completed: deduct stock
        elif old_status == 'cancelled' and new_status == 'completed':
            if product.stock <= 0:
                messages.error(request, f'🚨 Cannot complete! "{product.name}" is OUT OF STOCK!')
                return redirect('orders')
            if order.quantity > product.stock:
                messages.error(request, f'🚨 Only {product.stock} units available!')
                return redirect('orders')
            product.stock -= order.quantity
            product.save()
            messages.success(request, f'✅ Order completed! Stock reduced.')

        # ✅ Save new status
        order.status = new_status
        order.save()

        # ✅ Low stock warning after any change
        product.refresh_from_db()
        if product.stock == 0:
            messages.error(request, f'🚨 ALERT: "{product.name}" is now OUT OF STOCK!')
        elif product.stock <= product.low_stock_threshold:
            messages.warning(request, f'⚠️ WARNING: "{product.name}" only has {product.stock} units left!')

        return redirect('orders')

    return redirect('orders')


def delete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    # ✅ Restore stock if completed order is deleted
    if order.status == 'completed':
        order.product.stock += order.quantity
        order.product.save()
        messages.warning(request, f'⚠️ Order deleted. {order.quantity} units restored to "{order.product.name}".')
    else:
        messages.success(request, 'Order deleted.')

    order.delete()
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