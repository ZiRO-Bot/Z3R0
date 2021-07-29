import random


# Loot table based on MCJE 1.16.1
LOOT_TABLE = [
    (5, "enchanted-book"),
    (8, "iron-boots"),
    (10, "iron-nugget"),
    (10, "splash-potion-fire-res"),
    (10, "potion-fire-res"),
    (20, "quartz"),
    (20, "glowstone-dust"),
    (20, "magma-cream"),
    (20, "ender-pearl"),
    (20, "string"),
    (40, "fire-charge"),
    (40, "gravel"),
    (40, "leather"),
    (40, "nether-brick"),
    (40, "obsidian"),
    (40, "cry-obsidian"),
    (40, "soul-sand"),
]

# Item's name
NAME = {
    "enchanted-book": "Enchanted Book - Soul Speed",
    "iron-boots": "Enchanted Iron Boots - Soul Speed",
    "iron-nugget": "Iron Nuggets",
    "splash-potion-fire-res": "Splash Potion - Fire Resistance",
    "potion-fire-res": "Potion - Fire Resistance",
    "quartz": "Nether Quartz",
    "glowstone-dust": "Glowstone Dust",
    "magma-cream": "Magma Cream",
    "ender-pearl": "Ender Pearls",
    "string": "String",
    "fire-charge": "Fire Charge",
    "gravel": "Gravel",
    "leather": "Leather",
    "nether-brick": "Nether Bricks",
    "obsidian": "Obsidian",
    "cry-obsidian": "Crying Obsidian",
    "soul-sand": "Soul Sand",
}

# Item's quantity range
QUANTITY = {
    "iron-nugget": (9, 36),
    "quartz": (8, 16),
    "glowstone-dust": (5, 12),
    "magma-cream": (2, 6),
    "ender-pearl": (4, 8),
    "string": (8, 24),
    "fire-charge": (1, 5),
    "gravel": (8, 16),
    "leather": (4, 10),
    "nether-brick": (4, 16),
    "cry-obsidian": (1, 3),
    "soul-sand": (4, 16),
}


class Piglin:
    """
    A very messy Piglin Barter in python
    Based on outdated piglin loot table (MCJE 1.16.1)

    Created for ziBot
    """

    def __init__(self, gold: int = 64):
        items = []
        weights = []
        for loot in LOOT_TABLE:
            weights.append(loot[0])
            items.append(loot[1])
        self.items = [
            BarterItem(random.choices(items, weights=weights)[0]) for i in range(gold)
        ]

    def __str__(self):
        return ", ".join(
            ["{}: {}".format(str(item), item.quantity) for item in self.items]
        )


class BarterItem:

    __slots__ = ("id", "name", "quantity")

    def __init__(self, _id):
        self.id = _id
        self.name = NAME.get(_id)
        q = QUANTITY.get(_id, 1)
        self.quantity = q if not isinstance(q, tuple) else random.randrange(q[0], q[1])

    def __str__(self):
        return self.name
