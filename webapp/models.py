from dataclasses import dataclass

from monopoly.statements import Transaction


@dataclass
class TransactionMetadata:
    bank_name: str
    categorizer: str | None = None


@dataclass
class ProcessedFile:
    transactions: list[Transaction]
    metadata: TransactionMetadata
    categories: list[str] | None = None

    def __iter__(self):
        return iter(self.transactions)
