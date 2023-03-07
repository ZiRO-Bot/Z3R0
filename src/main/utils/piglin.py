"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import random


# Loot table based on MCJE 1.16.1 and MCBE Beta 1.16.0.57
LOOT_TABLE = [
    {
        "id": "netherite-hoe",
        "name": "Netherite Hoe",
        "weight": 1,
    },
    {
        "id": "enchanted-book",
        "name": "Enchanted Book - Soul Speed",
        "weight": 5,
    },
    {
        "id": "iron-boots",
        "name": "Enchanted Iron Boots - Soul Speed",
        "weight": 8,
    },
    {
        "id": "iron-nugget",
        "name": "Iron Nuggets",
        "weight": 10,
        "quantity": (9, 36),
    },
    {
        "id": "splash-potion-fire-res",
        "name": "Splash Potion - Fire Resistance",
        "weight": 10,
    },
    {
        "id": "potion-fire-res",
        "name": "Potion - Fire Resistance",
        "weight": 10,
    },
    {
        "id": "quartz",
        "name": "Nether Quartz",
        "weight": 20,
        "quantity": (8, 16),
    },
    {
        "id": "glowstone-dust",
        "name": "Glowstone Dust",
        "weight": 20,
        "quantity": (5, 12),
    },
    {
        "id": "magma-cream",
        "name": "Magma Cream",
        "weight": 20,
        "quantity": (2, 6),
    },
    {
        "id": "ender-pearl",
        "name": "Ender Pearls",
        "weight": 20,
        "quantity": (4, 8),
    },
    {
        "id": "string",
        "name": "String",
        "weight": 20,
        "quantity": (8, 24),
    },
    {
        "id": "fire-charge",
        "name": "Fire Charge",
        "weight": 40,
        "quantity": (1, 5),
    },
    {
        "id": "gravel",
        "name": "Gravel",
        "weight": 40,
        "quantity": (8, 16),
    },
    {
        "id": "leather",
        "name": "Leather",
        "weight": 40,
        "quantity": (4, 10),
    },
    {
        "id": "nether-brick",
        "name": "Nether Brick",
        "weight": 40,
        "quantity": (4, 16),
    },
    {
        "id": "obsidian",
        "name": "Obsidian",
        "weight": 40,
    },
    {
        "id": "cry-obsidian",
        "name": "Crying Obsidian",
        "weight": 40,
        "quantity": (1, 3),
    },
    {
        "id": "soul-sand",
        "name": "Soul Sand",
        "weight": 40,
        "quantity": (4, 16),
    },
]

# After the nerf
LOOT_TABLE_NERFED = [
    {
        "id": "enchanted-book",
        "name": "Enchanted Book - Soul Speed",
        "weight": 5,
    },
    {
        "id": "iron-boots",
        "name": "Enchanted Iron Boots - Soul Speed",
        "weight": 8,
    },
    {
        "id": "splash-potion-fire-res",
        "name": "Splash Potion - Fire Resistance",
        "weight": 8,
    },
    {
        "id": "potion-fire-res",
        "name": "Potion - Fire Resistance",
        "weight": 8,
    },
    {
        "id": "water-bottle",
        "name": "Water Bottle",
        "weight": 10,
    },
    {
        "id": "iron-nugget",
        "name": "Iron Nuggets",
        "weight": 10,
        "quantity": (10, 36),
    },
    {
        "id": "ender-pearl",
        "name": "Ender Pearls",
        "weight": 10,
        "quantity": (2, 4),
    },
    {
        "id": "string",
        "name": "String",
        "weight": 20,
        "quantity": (3, 9),
    },
    {
        "id": "quartz",
        "name": "Nether Quartz",
        "weight": 20,
        "quantity": (5, 12),
    },
    {
        "id": "obsidian",
        "name": "Obsidian",
        "weight": 40,
    },
    {
        "id": "cry-obsidian",
        "name": "Crying Obsidian",
        "weight": 40,
        "quantity": (1, 3),
    },
    {
        "id": "fire-charge",
        "name": "Fire Charge",
        "weight": 40,
    },
    {
        "id": "leather",
        "name": "Leather",
        "weight": 40,
        "quantity": (2, 4),
    },
    {
        "id": "soul-sand",
        "name": "Soul Sand",
        "weight": 40,
        "quantity": (2, 8),
    },
    {
        "id": "nether-brick",
        "name": "Nether Brick",
        "weight": 40,
        "quantity": (2, 8),
    },
    {
        "id": "spectral-arrow",
        "name": "Spectral Arrow",
        "weight": 40,
        "quantity": (6, 12),
    },
    {
        "id": "gravel",
        "name": "Gravel",
        "weight": 40,
        "quantity": (8, 16),
    },
    {
        "id": "blackstone",
        "name": "Blackstone",
        "weight": 40,
        "quantity": (8, 16),
    },
]


class Piglin:
    """
    A very messy Piglin Barter in python
    Based on outdated piglin loot table (MCJE 1.16.1)

    Created for ziBot
    """

    def __init__(self, gold: int = 64, lootTable: int = 0):
        _lootTable = LOOT_TABLE if lootTable == 0 else LOOT_TABLE_NERFED
        weights = []
        for loot in _lootTable:
            weights.append(loot["weight"])
        self.items = [BarterItem(random.choices(_lootTable, weights=weights)[0]) for _ in range(gold)]

    def __str__(self):
        return ", ".join(["{}: {}".format(str(item), item.quantity) for item in self.items])


class BarterItem:

    __slots__ = ("id", "name", "quantity")

    def __init__(self, item):
        self.id = item["id"]
        self.name = item["name"]
        q = item.get("quantity", 1)
        self.quantity = q if not isinstance(q, tuple) else random.randrange(q[0], q[1])

    def __str__(self):
        return self.name
