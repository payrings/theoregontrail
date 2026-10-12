"""The goods table ``S$(0 to 6, 0 to 3)``: name, base price, unit, plural ending.

Used by the forts, by trading and by the broken-part messages, so it carries the
unit and the plural ending as well as the price. Index 2 is ammunition, whose base
price of 2.00 is a *box* of twenty: the forts multiply the quantity by twenty at
``BUY.LIB`` 50025 and the trader divides it by twenty at ``TRADE.LIB`` 50011, which
is why the unit values the paper quotes (oxen 20, clothing 10, bullets 0.10,
wheels 10, axles 10, tongues 10, food 0.20) are not the table's prices.
"""

__all__ = ["S", "NAME", "PRICE", "UNIT", "PLURAL", "OXEN", "CLOTHING", "AMMO",
           "WHEELS", "AXLES", "TONGUES", "FOOD", "BOXES_PER_BULLETS"]

#                 name            price  unit     plural
S = [
    ["Oxen", 20.0, "ox", "en"],          # 0
    ["Clothing", 10.0, "set", "s"],      # 1
    ["Ammunition", 2.00, "box", "es"],   # 2
    ["Wagon wheels", 10.0, "wheel", "s"],  # 3
    ["Wagon axles", 10.0, "axle", "s"],    # 4
    ["Wagon tongues", 10.0, "tongue", "s"],  # 5
    ["Food", 0.20, "pound", "s"],         # 6
]
NAME = [r[0] for r in S]
PRICE = [r[1] for r in S]
UNIT = [r[2] for r in S]
PLURAL = [r[3] for r in S]

OXEN, CLOTHING, AMMO, WHEELS, AXLES, TONGUES, FOOD = range(7)

BOXES_PER_BULLETS = 20          # BUY.LIB 50025: K = 1 + 19 * (L = 3)
