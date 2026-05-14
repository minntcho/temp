from __future__ import annotations

from faker import Faker

LOCALE_BY_COUNTRY = {
    "KR": "ko_KR",
    "US": "en_US",
    "PL": "pl_PL",
    "CN": "zh_CN",
    "ID": "id_ID",
    "VN": "vi_VN",
}


def faker_for(country: str, seed: int) -> Faker:
    locale = LOCALE_BY_COUNTRY.get(country, "en_US")
    fake = Faker(locale)
    fake.seed_instance(seed)
    return fake


def generate_entity_name(*, country: str, entity_index: int, seed: int) -> str:
    fake = faker_for(country, seed + entity_index * 101)
    base = fake.company()
    return f"LGES Synthetic {base} SYN-{country}-{entity_index:03d}"


def generate_supplier_name(*, country: str, supplier_index: int, seed: int) -> str:
    fake = faker_for(country, seed + supplier_index * 1009)
    base = fake.company()
    return f"{base} SYN-{country}-{supplier_index:06d}"
