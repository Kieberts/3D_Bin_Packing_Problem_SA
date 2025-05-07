#!/usr/bin/env python3
# box_selection.py

import pulp

def main():
    # boxes = [
    #     {"name": "S", "length": 30, "height": 20, "depth": 10, "max_weight": 10, "volume": 6000},
    #     {"name": "M", "length": 40, "height": 30, "depth": 20, "max_weight": 20, "volume": 24000},
    #     {"name": "L", "length": 50, "height": 40, "depth": 30, "max_weight": 30, "volume": 60000},
    #     {"name": "XL", "length": 1000, "height": 1000, "depth": 1000, "max_weight": 80, "volume": 1000000000},
    # ]


    # products = [
    #     {"name": "Prod1", "length": 12, "height": 7, "depth": 3, "weight": 0.4, "volume": 252},
    #     {"name": "Prod2", "length": 15, "height": 20, "depth": 10, "weight": 0.3, "volume": 300},
    #     {"name": "Prod3", "length": 8, "height": 8, "depth": 3, "weight": 0.1, "volume": 192},
    #     {"name": "Prod3", "length": 10, "height": 10, "depth": 10, "weight": 1, "volume": 1000},
    # ]

    boxes = [
        {"name": "S", "length": 20, "height": 20, "depth": 15, "max_weight": 3, "volume": 6000},
        {"name": "M", "length": 25, "height": 25, "depth": 20, "max_weight": 4, "volume":  12500},
        {"name": "L", "length": 30, "height": 30, "depth": 25, "max_weight": 6, "volume": 22500},
        {"name": "XL", "length": 35, "height": 35, "depth": 30, "max_weight": 8, "volume": 36750},
        {"name": "XL", "length": 40, "height": 40, "depth": 35, "max_weight": 10, "volume": 56000},
    ]


    products = [
        {"name": "Smartphone", "length": 15, "height": 7, "depth": 1, "weight": 0.2, "volume": 105}, # no constraints
        {"name": "Watch", "length": 8, "height": 8, "depth": 3, "weight": 0.1, "volume": 192}, # no constraints
        {"name": "Headphones", "length": 20, "height": 15, "depth": 10, "weight": 0.3, "volume": 3000}, # no constraints
        {"name": "Headphones", "length": 20, "height": 15, "depth": 10, "weight": 0.3, "volume": 3000}, # no constraints
        {"name": "Digital Camera", "length": 12, "height": 8, "depth": 7, "weight": 0.5, "volume": 672}, # upright
    ]

    # products = [
    #     {"id": "Smartphone", "w": 15, "h": 7, "d": 1, "weight": 0.2, "upright_only": False}, # no constraints
    #     {"id": "Watch", "w": 8, "h": 8, "d": 3, "weight": 0.1, "upright_only": False}, # no constraints
    #     # {"id": "Headphones", "w": 20, "h": 15, "d": 10, "weight": 0.3, "upright_only": False}, # no constraints
    #     # {"id": "Headphones", "w": 20, "h": 15, "d": 10, "weight": 0.3, "upright_only": False}, # no constraints
    #     {"id": "Digital Camera", "w": 12, "h": 8, "d": 7, "weight": 0.5, "upright_only": False}, # upright
    # ]

    # Summen aus Produkten
    total_volume = sum(prod["volume"] for prod in products)
    total_weight = sum(prod["weight"] for prod in products)

    num_boxes = len(boxes)

    # Formulierung des MIP
    # Erstelle ein Minimierungsproblem
    model = pulp.LpProblem("Box_Selection", pulp.LpMinimize)

    # Binäre Variablen x_j: 1, wenn Box j gewählt, sonst 0
    x = [
        pulp.LpVariable(f"x_{j}", cat=pulp.LpBinary)
        for j in range(num_boxes)
    ]

    # Zielfunktion: Minimierung des Volumens der gewählten Box
    model += pulp.lpSum([boxes[j]["volume"] * x[j] for j in range(num_boxes)]), "Minimize_Box_Volume"

    # Nebenbedingung 1: Genau eine Box wird gewählt
    model += pulp.lpSum([x[j] for j in range(num_boxes)]) == 1, "Exactly_One_Box"

    # Nebenbedingung 2: Gesamtvolumen der Produkte <= Volumen der gewählten Box
    #   sum_i(prod_i_vol) <= sum_j( x_j * Box_j_Vol )
    # Da genau eine Box gewählt werden soll, reicht dies als globale Bedingung:
    model += total_volume <= pulp.lpSum([boxes[j]["volume"] * x[j] for j in range(num_boxes)]), "Volume_Constraint"

    # Nebenbedingung 3: Gesamtgewicht der Produkte <= Traglast der gewählten Box
    model += total_weight <= pulp.lpSum([boxes[j]["max_weight"] * x[j] for j in range(num_boxes)]), "Weight_Constraint"


    # Problem lösen
    print("\nLöse das Optimierungsproblem ...")
    solution_status = model.solve(pulp.PULP_CBC_CMD(msg=False))

    # Auswertung des Ergebnisses
    print(f"Status: {pulp.LpStatus[solution_status]}")

    if pulp.LpStatus[solution_status] == "Optimal":
        # Finde die (einzige) Box mit x_j = 1
        chosen_box_index = None
        for j in range(num_boxes):
            if pulp.value(x[j]) > 0.5:  # d.h. x_j = 1
                chosen_box_index = j
                break

        if chosen_box_index is not None:
            chosen_box = boxes[chosen_box_index]
            print("\n=== Ergebnis ===")
            print("Alle Produkte passen in folgende Box:")
            print(f"  Name:       {chosen_box['name']}")
            print(f"  Abmessungen: {chosen_box['length']} x {chosen_box['height']} x {chosen_box['depth']}")
            print(f"  Volumen:    {chosen_box['volume']}")
            print(f"  Traglast:   {chosen_box['max_weight']}")
            print("-------------------------------")
            print(f"Gesamtvolumen der Produkte: {total_volume}")
            print(f"Gesamtgewicht der Produkte: {total_weight}")
        else:
            print("\nKein eindeutig gewähltes x_j gefunden, etwas ist schiefgelaufen.")
    else:
        print("\nKeine zulässige Lösung gefunden. Möglicherweise passen die Produkte in keine der angegebenen Boxen.")


if __name__ == "__main__":
    main()
