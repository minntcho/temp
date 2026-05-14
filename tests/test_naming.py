from __future__ import annotations

import unittest

from synthetic_esg.naming import generate_entity_name, generate_supplier_name


class NamingTests(unittest.TestCase):
    def test_generated_names_keep_synthetic_marker(self) -> None:
        entity_name = generate_entity_name(country="KR", entity_index=1, seed=42)
        supplier_name = generate_supplier_name(country="US", supplier_index=1, seed=42)

        self.assertIn("SYN-KR-001", entity_name)
        self.assertIn("SYN-US-000001", supplier_name)

    def test_generated_names_are_seed_reproducible(self) -> None:
        first = generate_supplier_name(country="PL", supplier_index=7, seed=123)
        second = generate_supplier_name(country="PL", supplier_index=7, seed=123)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
