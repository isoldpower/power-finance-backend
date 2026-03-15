from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist

from finances.application.interfaces import WalletRepository
from finances.domain.entities import Wallet

from ..mappers import WalletMapper
from ..orm import WalletModel


class DjangoWalletRepository(WalletRepository):
    def get_user_wallet_by_id(self, wallet_id: UUID, user_id: int) -> Wallet:
        requested_wallet: WalletModel = WalletModel.objects.get(id=wallet_id, user_id=user_id)

        return WalletMapper.to_domain(requested_wallet)

    def get_user_wallet_for_update(self, wallet_id: UUID, user_id: int) -> Wallet:
        requested_wallet: WalletModel = (WalletModel.objects
            .select_for_update()
            .get(id=wallet_id, user_id=user_id))

        return WalletMapper.to_domain(requested_wallet)

    def soft_delete_wallet(self, wallet_id: UUID, user_id: int) -> Wallet:
        try:
            requested_wallet: WalletModel = WalletModel.objects.get(
                id=wallet_id,
                user_id=user_id,
            )
        except WalletModel.DoesNotExist:
            raise ObjectDoesNotExist("Wallet with specified ID does not exist.")

        requested_wallet.delete()
        requested_wallet.refresh_from_db()

        return WalletMapper.to_domain(requested_wallet)

    def create_wallet(self, wallet: Wallet) -> Wallet:
        created_wallet: WalletModel = WalletModel()

        WalletMapper.update_model(created_wallet, wallet)
        created_wallet.save()

        return WalletMapper.to_domain(created_wallet)

    def get_wallet_by_id(self, wallet_id: UUID) -> Wallet:
        requested_wallet: WalletModel = WalletModel.objects.get(id=wallet_id)

        return WalletMapper.to_domain(requested_wallet)

    def get_user_wallets(self, user_id: int) -> list[Wallet]:
        user_wallets = WalletModel.objects.filter(user_id=user_id).order_by("-created_at", "id")

        return [WalletMapper.to_domain(wallet) for wallet in user_wallets]

    def get_ordered_user_wallets(self, user_id: int) -> list[Wallet]:
        user_wallets = WalletModel.objects.filter(user_id=user_id).order_by('created_at', 'id')

        return [WalletMapper.to_domain(wallet) for wallet in user_wallets]

    def save_wallet(self, wallet: Wallet) -> Wallet:
        requested_wallet = WalletModel.objects.get(id=wallet.id)
        modified_fields = WalletMapper.get_changed_fields(requested_wallet, wallet)

        WalletMapper.update_model(requested_wallet, wallet)

        requested_wallet.save(update_fields=modified_fields)
        return WalletMapper.to_domain(requested_wallet)