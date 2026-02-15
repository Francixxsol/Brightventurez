from core.models import Transaction, WalletTransaction

for tx in Transaction.objects.all():
    WalletTransaction.objects.create(
        user=tx.user,
        reference=tx.reference,
        amount=tx.amount,
        transaction_type=tx.type,        # map type -> transaction_type
        status=tx.status,
        description=tx.note             # map note -> description
    )
print("Migration completed!")
