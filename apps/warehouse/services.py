import uuid
import logging
from django.db import transaction, DatabaseError, IntegrityError
from django.utils import timezone
from django.db.models import Sum, F

logger = logging.getLogger(__name__)

# Idempotent takroriy so'rovlar uchun qaytariladigan xabarlar.
# Chaqiruvchi (view) (True, <shu xabar>) ni "hech narsa o'zgarmadi" deb tushunadi.
ALREADY_RECEIVED = 'Allaqachon qabul qilingan'
ALREADY_PICKED = "Allaqachon yig'ilgan"
ALREADY_ALLOCATED = 'Allaqachon ajratilgan'
ALREADY_PROCESSED = 'Allaqachon qayta ishlangan'
ALREADY_DONE_MESSAGES = {ALREADY_RECEIVED, ALREADY_PICKED, ALREADY_ALLOCATED, ALREADY_PROCESSED}


def allocate_stock(order_item, performed_by=None):
    """
    FEFO/FIFO based atomic stock allocation.
    Returns (True, '') on success or (False, error_msg) on failure.
    Prevents double allocation: the order item row is locked before
    existing allocations are counted, so parallel requests serialize.
    """
    from apps.warehouse.models import InventoryBatch
    from apps.logistics.models import OrderItem, StockAllocation

    try:
        with transaction.atomic():
            item = (
                OrderItem.objects.select_for_update()
                .select_related('product', 'order__warehouse')
                .get(pk=order_item.pk)
            )
            product = item.product
            warehouse = item.order.warehouse
            needed = item.requested_quantity

            existing = StockAllocation.objects.filter(
                order_item=item
            ).aggregate(total=Sum('reserved_quantity'))['total'] or 0

            if existing >= needed:
                logger.info(f'Order item {item.pk} already fully allocated ({existing}/{needed})')
                return True, ALREADY_ALLOCATED

            remaining_needed = needed - existing
            now = timezone.now().date()

            # Select batches with lock to prevent race conditions
            if product.is_perishable:
                # FEFO: earliest expiry first, exclude expired and no-expiry
                batches = InventoryBatch.objects.filter(
                    product=product,
                    location__warehouse=warehouse,
                    condition='available',
                    expiry_date__isnull=False,
                    expiry_date__gt=now,  # not expired
                ).order_by('expiry_date', 'received_at').select_for_update()
            else:
                # FIFO: earliest received first
                batches = InventoryBatch.objects.filter(
                    product=product,
                    location__warehouse=warehouse,
                    condition='available',
                ).order_by('received_at').select_for_update()
            batches = list(batches)

            total_available = sum(max(0, b.quantity_on_hand - b.quantity_reserved) for b in batches)
            if total_available < remaining_needed:
                return False, (
                    f"Yetarli zaxira yo'q. Kerak: {remaining_needed}, "
                    f"mavjud: {total_available}"
                )

            remaining = remaining_needed
            for batch in batches:
                if remaining <= 0:
                    break
                avail = batch.quantity_on_hand - batch.quantity_reserved
                if avail <= 0:
                    continue
                take = min(avail, remaining)
                # (order_item, inventory_batch) unique — qisman ajratilgan partiyaga
                # qayta ajratishda mavjud yozuv oshiriladi
                alloc, created = StockAllocation.objects.get_or_create(
                    order_item=item,
                    inventory_batch=batch,
                    defaults={'reserved_quantity': take, 'picked_quantity': 0},
                )
                if not created:
                    StockAllocation.objects.filter(pk=alloc.pk).update(
                        reserved_quantity=F('reserved_quantity') + take
                    )
                InventoryBatch.objects.filter(pk=batch.pk).update(
                    quantity_reserved=F('quantity_reserved') + take
                )
                remaining -= take

            logger.info(
                f'Allocated {remaining_needed} units of {product.sku} '
                f'for order item {item.pk}'
            )
            return True, ''

    except DatabaseError as e:
        logger.error(f'Stock allocation DB error for order_item {order_item.pk}: {e}')
        return False, f'Bazaviy xato: {str(e)}'


def deallocate_stock(order_item, performed_by=None):
    """
    Releases all stock reservations for an order item.
    Idempotent - safe to call multiple times.
    """
    from apps.logistics.models import StockAllocation
    from apps.warehouse.models import InventoryBatch

    try:
        with transaction.atomic():
            allocations = StockAllocation.objects.filter(
                order_item=order_item,
                reserved_quantity__gt=0,
            ).select_related('inventory_batch').select_for_update()

            for alloc in allocations:
                batch = alloc.inventory_batch
                # Only release what hasn't been picked yet
                to_release = alloc.reserved_quantity - alloc.picked_quantity
                if to_release > 0:
                    InventoryBatch.objects.filter(pk=batch.pk).update(
                        quantity_reserved=F('quantity_reserved') - to_release
                    )
                alloc.reserved_quantity = alloc.picked_quantity
                alloc.save(update_fields=['reserved_quantity'])

            logger.info(f'Deallocated stock for order_item {order_item.pk}')
            return True, ''
    except DatabaseError as e:
        logger.error(f'Deallocation error for order_item {order_item.pk}: {e}')
        return False, str(e)


def receive_inbound_item(inbound_item, received_qty, performed_by=None, idempotency_key=None):
    """
    Creates/updates InventoryBatch when receiving an inbound item.
    Idempotency: if a movement with the same idempotency_key exists, nothing
    changes and (True, ALREADY_RECEIVED) is returned.
    """
    from apps.warehouse.models import InventoryBatch, StockMovement
    from apps.logistics.models import InboundItem

    if idempotency_key is None:
        idempotency_key = str(uuid.uuid4())

    try:
        with transaction.atomic():
            # Bir xil kalitli parallel so'rovlar shu qulfda navbatga turadi
            item = InboundItem.objects.select_for_update().select_related(
                'product', 'target_location', 'shipment'
            ).get(pk=inbound_item.pk)

            if StockMovement.objects.filter(idempotency_key=idempotency_key).exists():
                logger.info(f'Inbound item {item.pk} already received (idempotency: {idempotency_key})')
                return True, ALREADY_RECEIVED

            product = item.product
            location = item.target_location
            batch_number = item.batch_number or f'BATCH-{item.pk}-{timezone.now().strftime("%Y%m%d")}'

            batch, created = InventoryBatch.objects.get_or_create(
                product=product,
                batch_number=batch_number,
                location=location,
                defaults={
                    'quantity_on_hand': 0,
                    'quantity_reserved': 0,
                    'received_at': timezone.now(),
                    'expiry_date': item.expiry_date,
                    'condition': 'available',
                }
            )
            if not created:
                batch = InventoryBatch.objects.select_for_update().get(pk=batch.pk)

            InventoryBatch.objects.filter(pk=batch.pk).update(
                quantity_on_hand=F('quantity_on_hand') + received_qty
            )

            InboundItem.objects.filter(pk=item.pk).update(
                received_quantity=F('received_quantity') + received_qty
            )
            item.refresh_from_db(fields=['received_quantity'])
            inbound_item.received_quantity = item.received_quantity

            StockMovement.objects.create(
                product=product,
                batch=batch,
                from_location=None,
                to_location=location,
                quantity=received_qty,
                movement_type='inbound',
                reference=item.shipment.shipment_number,
                performed_by=performed_by,
                idempotency_key=idempotency_key,
            )

            _create_audit_log(
                user=performed_by,
                action='receive_inbound',
                object_type='InboundItem',
                object_id=str(item.pk),
                details={
                    'received_qty': received_qty,
                    'batch_number': batch_number,
                    'product_sku': product.sku,
                }
            )

            logger.info(f'Received {received_qty} units of {product.sku} into batch {batch_number}')
            return True, ''

    except IntegrityError:
        # Parallel so'rov xuddi shu kalit bilan birinchi bo'lib yozib ulgurgan
        if StockMovement.objects.filter(idempotency_key=idempotency_key).exists():
            return True, ALREADY_RECEIVED
        logger.exception('Receive inbound item integrity error')
        return False, "Ma'lumotlar yaxlitligi xatosi"
    except DatabaseError as e:
        logger.error(f'Receive inbound item error: {e}')
        return False, str(e)


def process_pick(stock_allocation, picked_qty, performed_by=None, idempotency_key=None):
    """
    Records picking of a stock allocation.
    Validates that picked_qty doesn't exceed remaining reservation.
    Idempotent via idempotency_key.
    """
    from apps.warehouse.models import InventoryBatch, StockMovement
    from apps.logistics.models import OrderItem, StockAllocation

    if idempotency_key is None:
        idempotency_key = str(uuid.uuid4())

    if picked_qty <= 0:
        return False, "Yig'ilgan miqdor 0 dan katta bo'lishi kerak"

    try:
        with transaction.atomic():
            # Qulflash tartibi: order_item -> allocation -> batch (deadlock bo'lmasligi uchun doim bir xil)
            order_item = OrderItem.objects.select_for_update().select_related('order', 'product').get(
                pk=stock_allocation.order_item_id
            )
            allocation = StockAllocation.objects.select_for_update().get(pk=stock_allocation.pk)
            batch = InventoryBatch.objects.select_for_update().select_related('location').get(
                pk=allocation.inventory_batch_id
            )

            if StockMovement.objects.filter(idempotency_key=idempotency_key).exists():
                logger.info(f'Pick already processed (idempotency: {idempotency_key})')
                return True, ALREADY_PICKED

            remaining_to_pick = allocation.reserved_quantity - allocation.picked_quantity
            if picked_qty > remaining_to_pick:
                return False, (
                    f"Yig'ilayotgan miqdor ({picked_qty}) "
                    f"qolgan rezervatsiyadan ({remaining_to_pick}) oshib ketdi"
                )

            InventoryBatch.objects.filter(pk=batch.pk).update(
                quantity_on_hand=F('quantity_on_hand') - picked_qty,
                quantity_reserved=F('quantity_reserved') - picked_qty,
            )

            allocation.picked_quantity = allocation.picked_quantity + picked_qty
            allocation.save(update_fields=['picked_quantity'])

            total_picked = order_item.allocations.aggregate(
                total=Sum('picked_quantity')
            )['total'] or 0
            order_item.picked_quantity = total_picked
            order_item.is_picked = total_picked >= order_item.requested_quantity
            order_item.save(update_fields=['is_picked', 'picked_quantity'])

            StockMovement.objects.create(
                product=order_item.product,
                batch=batch,
                from_location=batch.location,
                to_location=None,
                quantity=picked_qty,
                movement_type='outbound',
                reference=order_item.order.order_number,
                performed_by=performed_by,
                idempotency_key=idempotency_key,
            )

            logger.info(f'Picked {picked_qty} units for allocation {allocation.pk}')
            return True, ''

    except IntegrityError:
        if StockMovement.objects.filter(idempotency_key=idempotency_key).exists():
            return True, ALREADY_PICKED
        logger.exception('Process pick integrity error')
        return False, "Ma'lumotlar yaxlitligi xatosi"
    except DatabaseError as e:
        logger.error(f'Process pick error: {e}')
        return False, str(e)


def process_return(return_record, performed_by=None):
    """
    Processes a return record:
    - sellable: adds to available inventory
    - damaged/quarantine: creates batch with appropriate condition
    The record row is locked, so parallel requests process it only once.
    """
    from apps.warehouse.models import InventoryBatch, StockMovement
    from apps.logistics.models import ReturnRecord

    try:
        with transaction.atomic():
            record = ReturnRecord.objects.select_for_update().select_related(
                'product', 'original_order__warehouse'
            ).get(pk=return_record.pk)

            if record.processed:
                return_record.processed = True
                return True, ALREADY_PROCESSED

            product = record.product
            condition_map = {
                'sellable': 'available',
                'damaged': 'damaged',
                'quarantine': 'quarantine',
            }
            batch_condition = condition_map.get(record.condition, 'quarantine')
            idempotency_key = f'return-{record.pk}'

            if StockMovement.objects.filter(idempotency_key=idempotency_key).exists():
                record.processed = True
                record.save(update_fields=['processed'])
                return_record.processed = True
                return True, ALREADY_PROCESSED

            batch = None
            if batch_condition == 'available' and record.original_order:
                existing = InventoryBatch.objects.filter(
                    product=product,
                    location__warehouse=record.original_order.warehouse,
                    condition='available',
                ).select_for_update().first()
                if existing:
                    batch = existing
                    InventoryBatch.objects.filter(pk=batch.pk).update(
                        quantity_on_hand=F('quantity_on_hand') + record.quantity
                    )

            if batch is None and record.original_order:
                location = record.original_order.warehouse.locations.filter(is_active=True).first()
                if location:
                    batch = InventoryBatch.objects.create(
                        product=product,
                        location=location,
                        batch_number=f'RET-{record.pk}-{timezone.now().strftime("%Y%m%d")}',
                        quantity_on_hand=record.quantity,
                        quantity_reserved=0,
                        received_at=timezone.now(),
                        condition=batch_condition,
                    )

            if batch:
                StockMovement.objects.create(
                    product=product,
                    batch=batch,
                    from_location=None,
                    to_location=batch.location,
                    quantity=record.quantity,
                    movement_type='return',
                    reference=f'RET-{record.pk}',
                    performed_by=performed_by,
                    idempotency_key=idempotency_key,
                )

            record.processed = True
            record.save(update_fields=['processed'])
            return_record.processed = True

            _create_audit_log(
                user=performed_by,
                action='process_return',
                object_type='ReturnRecord',
                object_id=str(record.pk),
                details={
                    'condition': record.condition,
                    'quantity': record.quantity,
                    'product_sku': product.sku,
                }
            )

            logger.info(f'Processed return {record.pk}: {record.quantity} of {product.sku}')
            return True, ''

    except IntegrityError:
        if StockMovement.objects.filter(idempotency_key=f'return-{return_record.pk}').exists():
            return True, ALREADY_PROCESSED
        logger.exception('Process return integrity error')
        return False, "Ma'lumotlar yaxlitligi xatosi"
    except DatabaseError as e:
        logger.error(f'Process return error: {e}')
        return False, str(e)


def cancel_order(order, performed_by=None):
    """
    Cancels an order and releases all stock reservations.
    Safe to call if order is already cancelled; the order row is locked
    so the status check and the cancellation happen atomically.
    """
    from apps.logistics.models import OutboundOrder

    try:
        with transaction.atomic():
            locked = OutboundOrder.objects.select_for_update().get(pk=order.pk)

            if locked.status == 'cancelled':
                return True, 'Buyurtma allaqachon bekor qilingan'
            if locked.status in ('shipped', 'completed'):
                return False, "Jo'natilgan yoki yakunlangan buyurtmani bekor qilib bo'lmaydi"

            for item in locked.items.all():
                ok, msg = deallocate_stock(item, performed_by=performed_by)
                if not ok:
                    raise DatabaseError(msg)

            locked.status = 'cancelled'
            locked.save(update_fields=['status'])
            order.status = 'cancelled'

            _create_audit_log(
                user=performed_by,
                action='cancel_order',
                object_type='OutboundOrder',
                object_id=str(locked.pk),
                details={'order_number': locked.order_number}
            )

            logger.info(f'Order {locked.order_number} cancelled by {performed_by}')
            return True, ''

    except DatabaseError as e:
        logger.error(f'Cancel order error: {e}')
        return False, str(e)


def _create_audit_log(user, action, object_type, object_id, details=None):
    """
    Helper to create audit log entries.
    Runs in its own savepoint: a failure here is logged and does not
    break the caller's transaction.
    """
    try:
        from apps.audit.models import AuditLog
        with transaction.atomic():
            AuditLog.objects.create(
                user=user,
                action=action,
                object_type=object_type,
                object_id=object_id,
                details=details or {},
            )
    except Exception as e:
        logger.warning(f'Failed to create audit log: {e}')
