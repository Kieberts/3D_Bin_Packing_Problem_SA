# from 00_archive.sim_annealing_algo import AdaptiveSimulatedAnnealingPacker
# from sim_annealing_v3 import SmallestBinPacker
from sim_annealing_v4 import ImprovedBinPacker
from sim_annealing_v5 import SimAnnealingBinPacker
import json

# def start_test(beta, alpha, initial_temperature, max_iter, pack_iterations, containers, products, small_container_preference=0.5): 
#     print("Starting Test")
#     # Erzeuge Instanz und führe Packing durch
#     packer = AdaptiveSimulatedAnnealingPacker(
#         containers, 
#         beta=beta,
#         alpha=alpha,
#         initial_temperature=initial_temperature,
#         max_iter=max_iter,
#         small_container_preference=small_container_preference
#     )

#     noBin = "NoBinFound"
#     counts = {noBin: 0, "S": 0, "M": 0, "L": 0, "XL": 0, "XXL": 0}
#     real_loop_count = 0
#     for _ in range(pack_iterations):

#         # neu
#         vaildResult = True
#         while(vaildResult):
#             real_loop_count += 1
#             iteration_result = packer.pack(products)
#             if iteration_result.get("container") is not None:
#                 vaildResult = False
                
#         container_name = iteration_result["container"].get("name")
#         if container_name in counts:
#             counts[container_name] += 1
#         #

#         # iteration_result = packer.pack(products)
#         # if iteration_result.get("container") is None:       
#         #     counts[noBin] += 1
#         # else:     
#         #     container_name = iteration_result["container"].get("name")
#         #     if container_name in counts:
#         #         counts[container_name] += 1

#     print("Amount of Loops needed: ", real_loop_count)
#     print("Test finished")
#     print(json.dumps(counts, indent=2))

#     return counts


# def start_test_v2(beta, alpha, initial_temperature, max_iter, pack_iterations, containers, products, small_container_preference=0.5): 
#     print("Starting Test V4")
#     # Erzeuge Instanz und führe Packing durch
#     packer = SmallestBinPacker(
#         containers=containers,
#     )

#     noBin = "NoBinFound"
#     counts = {noBin: 0, "S": 0, "M": 0, "L": 0, "XL": 0, "XXL": 0}
#     real_loop_count = 0
#     for _ in range(pack_iterations):
#         real_loop_count += 1
#         print("Loop: ", real_loop_count)
#         # neu
#         # vaildResult = True
#         # while(vaildResult):
#         #     real_loop_count += 1
#         #     iteration_result = packer.pack(products)
#         #     if iteration_result.get("container") is not None:
#         #         vaildResult = False
                
#         # container_name = iteration_result["container"].get("name")
#         # if container_name in counts:
#         #     counts[container_name] += 1
#         #

#         iteration_result = packer.pack(products)
#         if iteration_result.get("container") is None:       
#             counts[noBin] += 1
#         else:     
#             container_name = iteration_result["container"].get("name")
#             if container_name in counts:
#                 counts[container_name] += 1

#     print("Amount of Loops needed: ", real_loop_count)
#     print("Test finished")
#     print(json.dumps(counts, indent=2))

#     return counts

def start_test_v3(beta, alpha, initial_temperature, max_iter, pack_iterations, containers, products, small_container_preference=0.5): 
    print("Starting Test V4")
    # Erzeuge Instanz und führe Packing durch
    packer = ImprovedBinPacker(
        containers=containers,
    )

    noBin = "TotalAmountOfIterations"
    counts = {noBin: 0, "S": 0, "M": 0, "L": 0, "XL": 0, "XXL": 0}
    real_loop_count = 0
    for _ in range(pack_iterations):
        print("Loop: ", real_loop_count)
        vaildResult = True
        while(vaildResult):
            real_loop_count += 1
            iteration_result = packer.pack(products)
            if iteration_result.get("container") is not None:
                vaildResult = False
                
        container_name = iteration_result["container"].get("name")
        if container_name in counts:
            counts[container_name] += 1
    counts[noBin] = real_loop_count

    print("Test finished")
    print(json.dumps(counts, indent=2))

    return counts


def start_test_v5(beta, alpha, initial_temperature, max_iter, pack_iterations, containers, products, small_container_preference=0.5): 
    print("Starting Test V5")
    # Erzeuge Instanz und führe Packing durch
    packer = SimAnnealingBinPacker(
        containers=containers,
    )

    noBin = "TotalAmountOfIterations"
    counts = {noBin: 0, "S": 0, "M": 0, "L": 0, "XL": 0, "XXL": 0}
    real_loop_count = 0
    for _ in range(pack_iterations):
        print("Loop: ", real_loop_count)
        vaildResult = True
        while(vaildResult):
            real_loop_count += 1
            iteration_result = packer.pack(products)
            if iteration_result.get("container") is not None:
                vaildResult = False
                
        container_name = iteration_result["container"].get("name")
        if container_name in counts:
            counts[container_name] += 1
    counts[noBin] = real_loop_count

    print("Test finished")
    print(json.dumps(counts, indent=2))

    return counts

if __name__ == "__main__":
    # Definiere ein paar Container
    # containers = [
    #     {"name": "S", "W": 20, "H": 20, "D": 15, "max_weight": 3, "volume": 6000},
    #     {"name": "M", "W": 25, "H": 25, "D": 20, "max_weight": 4, "volume": 12500},
    #     {"name": "L", "W": 30, "H": 30, "D": 25, "max_weight": 6, "volume": 22500},
    #     {"name": "XL", "W": 35, "H": 35, "D": 30, "max_weight": 8, "volume": 36750},
    #     {"name": "XXL", "W": 40, "H": 40, "D": 35, "max_weight": 10, "volume": 56000},
    # ]

    containers = [
        {"name": "S", "W": 20, "H": 20, "D": 15, "max_weight": 3},
        {"name": "M", "W": 25, "H": 25, "D": 20, "max_weight": 4},
        {"name": "L", "W": 30, "H": 30, "D": 25, "max_weight": 6},
        {"name": "XL", "W": 35, "H": 35, "D": 30, "max_weight": 8},
        {"name": "XXL", "W": 40, "H": 40, "D": 35, "max_weight": 10},
    ]

    # products = [
    #     {"id": "Smartphone", "w": 15, "h": 7, "d": 1, "weight": 0.2, "upright_only": False},
    #     {"id": "Watch", "w": 8, "h": 8, "d": 3, "weight": 0.1, "upright_only": False},
    #     {"id": "Digital Camera", "w": 12, "h": 8, "d": 7, "weight": 0.5, "upright_only": False},
    #     {"id": "Headphones", "w": 20, "h": 15, "d": 10, "weight": 0.3, "upright_only": False},
    #     # {"id": "Headphones", "w": 20, "h": 15, "d": 10, "weight": 0.3, "upright_only": False},
    # ]

    products = [
        {"id": "Test1", "w": 2, "h": 2, "d": 3, "weight": 0.3, "upright_only": False},
        {"id": "Test2", "w": 2, "h": 2, "d": 3, "weight": 0.3, "upright_only": False},
        {"id": "Test3", "w": 2, "h": 2, "d": 3, "weight": 0.3, "upright_only": False},
        {"id": "Test4", "w": 2, "h": 2, "d": 3, "weight": 0.3, "upright_only": False},
        {"id": "Test5", "w": 2, "h": 2, "d": 3, "weight": 0.3, "upright_only": False},
        {"id": "Test6", "w": 2, "h": 2, "d": 3, "weight": 0.3, "upright_only": False},
    ]

    # products = [
    #     {"id": "Test1", "w": 2, "h": 2, "d": 3, "weight": 0.3, "upright_only": False},
    #     {"id": "Test2", "w": 2, "h": 2, "d": 3, "weight": 0.3, "upright_only": False},
    # ]
  

    # Algorithmus Parameter
    beta = 0.2 
    alpha = 0.002
    initial_temperature = 0.3  # Leicht erhöht für bessere Exploration
    max_iter = 1200  # Erhöht für gründlichere Suche
    pack_iterations = 2
    small_container_preference = 1 # Präferenz für kleinere Container
    
    # Führe den Algorithmus aus
    counts = start_test_v5(
        beta, 
        alpha, 
        initial_temperature, 
        max_iter, 
        pack_iterations,
        containers, 
        products,
        small_container_preference
    )
    
    print("Results:")
    print(json.dumps(counts, indent=2))