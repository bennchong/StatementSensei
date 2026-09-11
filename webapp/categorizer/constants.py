DEFAULT_RULES: dict[str, tuple[str, ...]] = {
    "Groceries": ("grocery", "supermarket", "whole foods", "trader joe"),
    "Dining": ("restaurant", "cafe", "coffee", "diner", "breakfast", "lunch", "dinner"),
    "Transport": ("uber", "lyft", "taxi", "train", "bus", "transit"),
    "Utilities": ("utility", "electric", "water", "gas", "internet"),
    "Shopping": ("amazon", "walmart", "target", "shop"),
    "Services": ("hair", "barber", "salon", "consulting"),
}

DEFAULT_CATEGORY = "Uncategorized"
DEFAULT_CATEGORIZER_NAME = "noop"
CATEGORIZER_ENV_VAR = "STATEMENTSENSEI_CATEGORIZER"