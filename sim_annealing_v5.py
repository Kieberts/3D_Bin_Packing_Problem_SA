import random
import math
import copy
import time

class SimAnnealingBinPacker:
    def __init__(self, containers):
        """
        Unified bin packer with optimized performance for finding the smallest suitable container.

        Parameters:
        -----------
        containers : list
            List of container definitions with 'W', 'H', 'D', and optional 'max_weight' and 'name'
        beta : float
            Cooling parameter for simulated annealing (currently not used in the provided SA logic)
        alpha : float
            Heating parameter for simulated annealing (currently not used in the provided SA logic)
        initial_temperature : float
            Starting temperature for simulated annealing
        max_iter : int
            Maximum iterations for simulated annealing per configuration start
        small_container_preference : float
            Preference factor for smaller containers (0-1) (currently not explicitly used, sorting handles preference)
        max_attempts_per_bin : int
            Maximum number of random restarts (attempts) per container
        time_limit : int
            Overall time limit in seconds for the packing process across all containers.
        """
        # Sort containers by volume, ascending, to try smallest first
        self.containers = sorted(containers, key=lambda c: c['W'] * c['H'] * c['D'])
        self.beta = 0.2 
        self.alpha = 00.2
        self.initial_temperature = 0.5
        self.max_iter = 2500
        self.small_container_preference = 1.0
        self.max_attempts_per_bin = 10
        self.time_limit = 30

        # Initialize with placeholders - these will be set per container during optimization
        self.products = []
        self.products_dict = {}
        self.n = 0
        self.W = 0 # Current container width
        self.H = 0 # Current container height
        self.D = 0 # Current container depth


    def get_coniguration(self):
        """
        Returns the current configuration parameters of the bin packer.
        """
        return {
            "beta": self.beta,
            "alpha": self.alpha,
            "initial_temperature": self.initial_temperature,
            "max_iter": self.max_iter,
            "small_container_preference": self.small_container_preference,
            "max_attempts_per_bin": self.max_attempts_per_bin,
            "time_limit": self.time_limit,
        }

    def _quick_assessment(self, products, container):
        """
        Perform quick feasibility checks to determine if products might fit in container.

        Returns:
        --------
        feasibility_score : float
            Score between 0-1 indicating likelihood of fit (1 = definitely fits)
        definitely_fits : bool
            True if products definitely fit based on simple checks
        definitely_too_small : bool
            True if container is definitely too small
        """
        # Check total volume
        total_product_volume = sum(p['w'] * p['h'] * p['d'] for p in products)
        container_volume = container['W'] * container['H'] * container['D']
        volume_ratio = total_product_volume / container_volume if container_volume > 0 else float('inf')

        # Check total weight
        total_weight = sum(p.get('weight', 0) for p in products)
        max_container_weight = container.get('max_weight', float('inf'))

        # Check largest single product dimensions
        if not products: return 1.0, True, False # Empty product list fits anything

        # Definite rejection conditions first
        if total_weight > max_container_weight:
            return 0.0, False, True

        # Check individual product dimensions against container, considering rotation
        container_dims_sorted = sorted([container['W'], container['H'], container['D']])
        epsilon = 1e-5
        for p in products:
            product_dims = [p['w'], p['h'], p['d']]
            if p.get('upright_only', False):
                 # Upright: Check if height fits, and rotated base fits rotated container base
                 if p['h'] > container['H'] + epsilon:
                     return 0.0, False, True
                 # Check if base (w, d) fits in container's (W, D) in either orientation
                 if not ((p['w'] <= container['W'] + epsilon and p['d'] <= container['D'] + epsilon) or \
                         (p['d'] <= container['W'] + epsilon and p['w'] <= container['D'] + epsilon)):
                     return 0.0, False, True
            else:
                 # Not upright: Check if sorted product dims fit sorted container dims
                 product_dims_sorted = sorted(product_dims)
                 if any(product_dims_sorted[i] > container_dims_sorted[i] + epsilon for i in range(3)):
                     return 0.0, False, True # Fails if smallest dim > smallest container dim, etc.

        # If individual checks pass, proceed with volume etc.
        if volume_ratio > 1.0 + epsilon: # Check volume ratio strictly now
            return 0.0, False, True

        # Special case: Single product (already checked dimensional fit)
        if len(products) == 1:
            return 1.0, True, False # If dimension check passed, it fits

        # Special case: Homogeneous products (all identical)
        if len(products) > 1 and all(p['w'] == products[0]['w'] and p['h'] == products[0]['h'] and
                                      p['d'] == products[0]['d'] and
                                      p.get('upright_only', False) == products[0].get('upright_only', False)
                                      for p in products):
            if volume_ratio > 0.95: # Very tight packing needed
                return 0.1, False, False
            if volume_ratio < 0.5:
                return 0.9, False, False

        # General feasibility score
        # Lower score if volume ratio is high, higher score if low
        feasibility_score = max(0.0, 1.0 - volume_ratio)

        # Definitely fits condition (conservative)
        definitely_fits = volume_ratio < 0.3

        # Definitely too small condition (already handled by dimension and volume checks above)
        definitely_too_small = False # If we reached here, it's not definitely too small by simple checks

        return feasibility_score, definitely_fits, definitely_too_small


    def _rotate_dimensions(self, box, orientation):
        """
        Returns the dimensions of a box in the specified orientation.

        Parameters:
        -----------
        box : dict
            Box with 'w', 'h', 'd' dimensions
        orientation : str
            Orientation code ('WHD', 'WDH', etc.)

        Returns:
        --------
        tuple
            (width, height, depth) in the specified orientation
        """
        w, h, d = box['w'], box['h'], box['d']
        if orientation == "WHD": return w, h, d
        elif orientation == "WDH": return w, d, h
        elif orientation == "HWD": return h, w, d
        elif orientation == "HDW": return h, d, w
        elif orientation == "DHW": return d, h, w
        elif orientation == "DWH": return d, w, h
        # Fallback for invalid orientation (should not happen with validation)
        return w, h, d

    # --- CORE PLACEMENT LOGIC ---
    def _place_boxes(self, sequence_A, sequence_B, sequence_C, orientations):
        """
        Attempts to place boxes according to given sequences and orientations,
        ensuring boxes rest on the floor (Y=0) or on top of other boxes (gravity).

        Parameters:
        -----------
        sequence_A, sequence_B, sequence_C : list
            Sequences of box IDs determining placement order and position constraints.
            Sequence B determines the order of insertion attempts.
        orientations : dict
            Mapping of box ID to orientation ('WHD', 'WDH', etc.)

        Returns:
        --------
        tuple
            (placement_list, utilization, valid)
            placement_list contains dicts with 'id', 'x', 'y', 'z', 'w', 'h', 'd', 'orientation'.
            utilization is the ratio of placed volume to container volume.
            valid is True if all boxes were placed successfully within bounds and constraints.
        """
        # Create lookup tables for sequence positions (relative ordering)
        pos_in_A = {seq_id: idx for idx, seq_id in enumerate(sequence_A)}
        # pos_in_B = {seq_id: idx for idx, seq_id in enumerate(sequence_B)} # Used only for insertion order below
        pos_in_C = {seq_id: idx for idx, seq_id in enumerate(sequence_C)}

        # Initialize placement tracking
        placed = {}  # id -> (x, y, z, w, h, d) : stores final placement coords and dims for quick lookup
        placement_list = [] # Stores detailed placement info for the result
        total_placed_volume = 0.0
        epsilon = 1e-5 # Tolerance for floating point comparisons

        # Process boxes in the order defined by sequence B
        for box_id in sequence_B:
            box = self.products_dict[box_id]
            ori = orientations[box_id]
            w_i, h_i, d_i = self._rotate_dimensions(box, ori) # Dimensions for current box i

            # --- Determine target (x, z) coordinates based on sequences A and C ---
            # Find the minimum required X based on items that must be to the left (sequence A)
            target_x = 0.0
            for j_id, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                # If item j must be placed before item i in sequence A (j is to the left of i)
                if pos_in_A[j_id] < pos_in_A[box_id]:
                    target_x = max(target_x, x_j + w_j) # i must start at or after the right edge of j

            # Find the minimum required Z based on items that must be behind (sequence C)
            target_z = 0.0
            for j_id, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                # If item j must be placed before item i in sequence C (j is behind i)
                if pos_in_C[j_id] < pos_in_C[box_id]:
                    target_z = max(target_z, z_j + d_j) # i must start at or after the front edge of j

            # --- Determine target y coordinate (Gravity/Support) ---
            # Find the highest point (y + height) among already placed boxes ('j')
            # whose XZ footprint overlaps with the *target* XZ footprint of the current box ('i').
            max_support_y = 0.0 # Default to floor level (Y=0)

            for j_id, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                # Check for overlap in the XZ plane between the target placement of box i
                # and the actual placement of already placed box j.
                overlap_x_min = max(target_x, x_j)
                overlap_x_max = min(target_x + w_i, x_j + w_j)
                overlap_z_min = max(target_z, z_j)
                overlap_z_max = min(target_z + d_i, z_j + d_j)

                # If there is a non-zero overlap area (greater than epsilon)
                has_xz_overlap = (overlap_x_max > overlap_x_min + epsilon) and \
                                 (overlap_z_max > overlap_z_min + epsilon)

                if has_xz_overlap:
                    # Box j is potentially underneath box i's target XZ position.
                    # The top surface of box j (y_j + h_j) is a potential support level.
                    # We need the highest such support level under the target footprint.
                    max_support_y = max(max_support_y, y_j + h_j)

            # Set the final y coordinate for box i. It will rest on the highest support found, or the floor.
            final_y = max_support_y

            # --- Validate Placement ---
            # 1. Check container bounds (using epsilon for safety)
            if (target_x + w_i > self.W + epsilon or
                final_y + h_i > self.H + epsilon or
                target_z + d_i > self.D + epsilon):
                # Placement failed: Box goes outside the container dimensions.
                return [], 0.0, False # Return empty list, zero utilization, invalid flag

            # 2. Overlap Check (Optional but good practice, though sequences should prevent it)
            # Check if the placed box 'i' overlaps with any already placed box 'j'
            # This check is somewhat redundant if sequence logic is perfect, but adds robustness.
            for j_id, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                # Check for 3D overlap
                overlap_x = (target_x < x_j + w_j - epsilon) and (target_x + w_i > x_j + epsilon)
                overlap_y = (final_y < y_j + h_j - epsilon) and (final_y + h_i > y_j + epsilon)
                overlap_z = (target_z < z_j + d_j - epsilon) and (target_z + d_i > z_j + epsilon)
                if overlap_x and overlap_y and overlap_z:
                     return [], 0.0, False # Placement failed due to overlap

            # --- Finalize Placement ---
            # If all checks passed, add the box to the placed dictionary and list
            placed[box_id] = (target_x, final_y, target_z, w_i, h_i, d_i)
            total_placed_volume += w_i * h_i * d_i

            placement_list.append({
                "id": box_id,
                "x": target_x, "y": final_y, "z": target_z,
                "w": w_i, "h": h_i, "d": d_i,
                "orientation": ori
                # Weight will be added in the final pack result format
            })

        # --- Calculate final utilization ---
        container_volume = self.W * self.H * self.D
        utilization = total_placed_volume / container_volume if container_volume > 0 else 0.0

        # If loop completes, all boxes were placed successfully according to the rules
        return placement_list, utilization, True
    # --- END OF CORE PLACEMENT LOGIC ---


    def _generate_initial_orientations(self, products, container=None):
        """
        Generate initial orientations for all products, prioritizing valid and potentially better fits.

        Parameters:
        -----------
        products : list
            List of product dictionaries
        container : dict, optional
            Container definition to check fit against

        Returns:
        --------
        dict
            Mapping of product ID to a plausible initial orientation
        """
        orientations = {}
        epsilon = 1e-5

        for product in products:
            product_id = product['id']

            if product.get('upright_only', False):
                # For upright products, only WHD (w,h,d -> W,H,D) and DHW (d,h,w -> W,H,D) are typically meaningful
                # Check if WHD fits container dims
                can_whd = False
                if container:
                     can_whd = (product['w'] <= container['W'] + epsilon and
                                product['h'] <= container['H'] + epsilon and
                                product['d'] <= container['D'] + epsilon)

                # Check if DHW fits container dims (d maps to W, h maps to H, w maps to D)
                can_dhw = False
                if container:
                    can_dhw = (product['d'] <= container['W'] + epsilon and
                               product['h'] <= container['H'] + epsilon and
                               product['w'] <= container['D'] + epsilon)

                if can_whd and can_dhw:
                     # If both fit, maybe prefer the one with smaller footprint W*D?
                     # WHD footprint = w*d, DHW footprint = d*w. They are the same. Default to WHD.
                     orientations[product_id] = "WHD"
                elif can_whd:
                     orientations[product_id] = "WHD"
                elif can_dhw:
                     orientations[product_id] = "DHW"
                else:
                     # If neither fits (should be caught by quick_assessment) or no container given, default.
                     orientations[product_id] = "WHD"
                continue # Go to next product

            # For regular (non-upright) products
            possible_orientations = ["WHD", "WDH", "HWD", "HDW", "DHW", "DWH"]
            valid_orientations = []

            if container:
                # Filter orientations that fit within the container dimensions
                for ori in possible_orientations:
                    w, h, d = self._rotate_dimensions(product, ori)
                    if w <= container['W'] + epsilon and h <= container['H'] + epsilon and d <= container['D'] + epsilon:
                        valid_orientations.append(ori)

                if not valid_orientations:
                    # This should ideally not happen if _quick_assessment passed.
                    # If it does, default to WHD, but the placement will likely fail later.
                    orientations[product_id] = "WHD"
                    continue

                # Score valid orientations (simple heuristic: prefer flatter orientations)
                best_score = -float('inf')
                best_ori = valid_orientations[0] # Default to first valid one

                for ori in valid_orientations:
                    w, h, d = self._rotate_dimensions(product, ori)
                    # Score: maximize base area (w*d), slightly penalize height (h)
                    # Using W*D as base assumes container's W, D are floor dimensions
                    score = (w * d) - (h * 0.1) # Heuristic score, small penalty for height
                    if score > best_score:
                        best_score = score
                        best_ori = ori
                orientations[product_id] = best_ori
            else:
                # Random orientation if no container provided for guidance
                orientations[product_id] = random.choice(possible_orientations)

        return orientations

    def _generate_starting_configurations(self, products, container, num_configs=10):
        """
        Generate diverse starting configurations (sequences and orientations) for optimization.

        Parameters:
        -----------
        products : list
            List of product dictionaries
        container : dict
            Container definition
        num_configs : int
            Number of configurations to generate

        Returns:
        --------
        list
            List of configuration dictionaries {'sequences': {'A':[], 'B':[], 'C':[]}, 'orientations': {}}
        """
        configs = []
        product_ids = [p['id'] for p in products]
        n_products = len(products)
        if n_products == 0: return []

        # --- Define Base Sequences based on Sorting Criteria ---
        base_seqs = {}
        # Volume
        base_seqs['volume_desc'] = [p['id'] for p in sorted(products, key=lambda p: p['w'] * p['h'] * p['d'], reverse=True)]
        base_seqs['volume_asc'] = base_seqs['volume_desc'][::-1]
        # Weight
        base_seqs['weight_desc'] = [p['id'] for p in sorted(products, key=lambda p: p.get('weight', 0.0), reverse=True)]
        base_seqs['weight_asc'] = base_seqs['weight_desc'][::-1]
        # Max Dimension
        base_seqs['max_dim_desc'] = [p['id'] for p in sorted(products, key=lambda p: max(p['w'], p['h'], p['d']), reverse=True)]
        base_seqs['max_dim_asc'] = base_seqs['max_dim_desc'][::-1]
        # Height (original H dim)
        base_seqs['height_desc'] = [p['id'] for p in sorted(products, key=lambda p: p['h'], reverse=True)]
        base_seqs['height_asc'] = base_seqs['height_desc'][::-1]
        # Width (original W dim)
        base_seqs['width_desc'] = [p['id'] for p in sorted(products, key=lambda p: p['w'], reverse=True)]
        base_seqs['width_asc'] = base_seqs['width_desc'][::-1]
        # Depth (original D dim)
        base_seqs['depth_desc'] = [p['id'] for p in sorted(products, key=lambda p: p['d'], reverse=True)]
        base_seqs['depth_asc'] = base_seqs['depth_desc'][::-1]


        # Generate initial orientations once, using the container for guidance
        initial_orientations = self._generate_initial_orientations(products, container)

        # Footprint based sorting (using the generated initial orientation)
        fit_scores = []
        for p in products:
             p_id = p['id']
             # Use the generated orientation for this product
             ori = initial_orientations.get(p_id, "WHD") # Get orientation or default
             w, h, d = self._rotate_dimensions(p, ori)
             footprint = w * d # Calculate footprint in the chosen orientation
             fit_scores.append({'id': p_id, 'footprint': footprint, 'oriented_h': h})

        # Sort by footprint (asc/desc) and oriented height (asc/desc)
        base_seqs['footprint_asc'] = [p['id'] for p in sorted(fit_scores, key=lambda x: x['footprint'])]
        base_seqs['footprint_desc'] = base_seqs['footprint_asc'][::-1]
        base_seqs['oriented_h_asc'] = [p['id'] for p in sorted(fit_scores, key=lambda x: x['oriented_h'])]
        base_seqs['oriented_h_desc'] = base_seqs['oriented_h_asc'][::-1]

        # Add a random sequence
        base_seqs['random'] = random.sample(product_ids, n_products)

        # --- Create Diverse Sequence Combinations ---
        seq_choices = list(base_seqs.keys())
        added_configs_repr = set() # Keep track of added sequence combinations (A, B, C) to avoid duplicates

        # Try some deterministic combinations first, aiming for variety
        # Sequence B often benefits from specific orders (e.g., small footprint first, or short items first)
        deterministic_combos = [
            # A (Left->Right), B (Insertion Order), C (Back->Front)
            ('volume_desc', 'footprint_asc', 'volume_desc'), # Large items left/back, insert small footprints first
            ('footprint_asc', 'footprint_asc', 'footprint_asc'), # Prioritize small footprints
            ('weight_desc', 'oriented_h_asc', 'footprint_asc'), # Heavy left, insert short first, small footprint back
            ('max_dim_desc', 'weight_desc', 'volume_desc'), # Max dim left, insert heavy first, large vol back
            ('volume_desc', 'volume_asc', 'volume_desc'), # Large left/back, insert small volume first
            ('width_desc', 'oriented_h_asc', 'depth_desc'), # Wide left, insert short first, deep back
            ('random', 'random', 'random'), # Pure random
        ]

        for combo in deterministic_combos:
             combo_repr = "-".join(combo)
             if combo_repr not in added_configs_repr:
                 # Ensure all sequence keys exist in base_seqs before using them
                 if all(k in base_seqs for k in combo):
                     configs.append({
                         'sequences': {
                             'A': base_seqs[combo[0]].copy(),
                             'B': base_seqs[combo[1]].copy(),
                             'C': base_seqs[combo[2]].copy()
                         },
                         'orientations': copy.deepcopy(initial_orientations) # Use the same initial orientations
                     })
                     added_configs_repr.add(combo_repr)
             if len(configs) >= num_configs: break

        # Add random combinations until num_configs is reached
        max_random_attempts = num_configs * 5 # Prevent potential infinite loop if choices are limited
        random_attempts = 0
        while len(configs) < num_configs and random_attempts < max_random_attempts:
            random_attempts += 1
            # Randomly select sequence types for A, B, C
            seq_A_key = random.choice(seq_choices)
            seq_B_key = random.choice(seq_choices)
            seq_C_key = random.choice(seq_choices)
            combo_repr = "-".join(sorted((seq_A_key, seq_B_key, seq_C_key))) # Use sorted tuple for uniqueness check

            if combo_repr not in added_configs_repr:
                 # Ensure keys exist before creating config
                 if all(k in base_seqs for k in [seq_A_key, seq_B_key, seq_C_key]):
                     configs.append({
                         'sequences': {
                             'A': base_seqs[seq_A_key].copy(),
                             'B': base_seqs[seq_B_key].copy(),
                             'C': base_seqs[seq_C_key].copy()
                         },
                         'orientations': copy.deepcopy(initial_orientations) # Use same initial orientations
                     })
                     added_configs_repr.add(combo_repr)

        # Ensure we don't exceed num_configs, even if deterministic combos filled it
        return configs[:num_configs]


    def _optimize_for_container(self, products, container, container_index):
        """
        Optimize product placement for a specific container using Simulated Annealing.
        """
        # Set current container dimensions for helper functions
        self.W = container['W']
        self.H = container['H']
        self.D = container['D']
        container_name = container.get('name', f'Container-{container_index}')
        container_volume = container['W'] * container['H'] * container['D']
        max_container_weight = container.get('max_weight', float('inf'))

        # Prepare product data for this optimization run
        self.products = products # Keep local copy (shallow is fine)
        self.n = len(products)
        if self.n == 0: # Handle empty product list
             return { "container_index": container_index, "container_name": container_name, "container_volume": container_volume, "valid": True, "utilization": 0.0, "placement": [], "best_config": None}

        self.products_dict = {prod['id']: prod for prod in products}

        # --- Quick Assessment ---
        feasibility_score, definitely_fits, definitely_too_small = self._quick_assessment(products, container)

        if definitely_too_small:
            return {
                "container_index": container_index, "container_name": container_name,
                "container_volume": container_volume, "valid": False,
                "message": "Container too small based on quick assessment (dims/vol/weight)"
            }
        # Weight check might be redundant if quick_assessment covers it, but good to be sure
        total_weight = sum(prod.get('weight', 0.0) for prod in products)
        if total_weight > max_container_weight:
            return {
                "container_index": container_index, "container_name": container_name,
                "container_volume": container_volume, "valid": False,
                "message": f"Total weight {total_weight:.2f} exceeds container limit {max_container_weight:.2f}"
            }

        # --- Simulated Annealing Setup ---
        iterations_per_config = max(200, int(self.max_iter / (1 + 0.1 * self.n))) # Fewer iters per config if many items? Or use fixed self.max_iter
        # iterations_per_config = self.max_iter # Use the configured value directly for now

        initial_temp = self.initial_temperature
        attempts = self.max_attempts_per_bin 

        # num_configs: More starting points if more items or time allows
        num_configs = max(3, min(15, int(5 + self.n * 0.3))) # More diverse starts for complex problems

        start_time = time.time()
        # Time limit for THIS container optimization is passed from pack()
        time_limit_per_container = self.current_container_time_limit # Get the budget for this container

        best_overall_util = -1.0
        best_overall_placement = None
        best_overall_config = None
        found_valid_solution = False

        # --- Outer Loop: Attempts (Random Restarts) ---
        for attempt in range(attempts):
            elapsed_total = time.time() - start_time
            if elapsed_total > time_limit_per_container:
                 break

            # Generate diverse starting configurations for this attempt
            start_configs = self._generate_starting_configurations(products, container, num_configs=num_configs)
            if not start_configs: continue # Should not happen if n > 0

            best_attempt_util = -1.0
            best_attempt_placement = None
            best_attempt_config = None

            # Estimate time budget per configuration within this attempt
            remaining_time_attempt = max(0, time_limit_per_container - elapsed_total)
            remaining_attempts = max(1, attempts - attempt)
            time_budget_this_attempt = remaining_time_attempt / remaining_attempts
            time_per_config = time_budget_this_attempt / len(start_configs) if start_configs else 0

            # --- Middle Loop: Starting Configurations ---
            for config_idx, config in enumerate(start_configs):
                config_start_time = time.time()
                # Check if time budget for this config is already exceeded (relative to start of attempt)
                if (config_start_time - start_time) > time_limit_per_container: break # Check overall time limit

                sequence_A = config['sequences']['A']
                sequence_B = config['sequences']['B']
                sequence_C = config['sequences']['C']
                orientations = config['orientations']

                # Evaluate initial placement using the CORE _place_boxes
                placement, util, valid = self._place_boxes(sequence_A, sequence_B, sequence_C, orientations)

                if not valid: continue # This starting config is invalid, try next

                # If valid, it's our current best for this SA run
                curr_seq_A, curr_seq_B, curr_seq_C = sequence_A.copy(), sequence_B.copy(), sequence_C.copy()
                curr_orient = orientations.copy()
                curr_util = util

                # Keep track of the best solution found starting from THIS config
                best_config_seq_A, best_config_seq_B, best_config_seq_C = curr_seq_A.copy(), curr_seq_B.copy(), curr_seq_C.copy()
                best_config_orient = curr_orient.copy()
                best_config_util = curr_util
                best_config_placement = placement # Store the placement corresponding to best_config_util

                # --- Inner Loop: Simulated Annealing ---
                T = initial_temp
                min_T = 1e-6 # Stop temperature
                # Cooling rate: adjust based on iterations to reach min_T near the end
                cooling_rate = math.exp(math.log(min_T / max(T, min_T)) / iterations_per_config) if iterations_per_config > 0 and T > min_T else 0.99

                iters_done = 0
                for it in range(iterations_per_config):
                    if T < min_T: break
                    # Check overall time limit frequently within SA loop
                    if time.time() - start_time > time_limit_per_container: break

                    # --- Generate Neighbor Solution ---
                    # Weights favor sequence swaps slightly more than orientation changes initially
                    move_weights = [1, 1, 1, 1, 1, 1.5] # Sum = 6.5
                    move_type = random.choices(range(1, 7), weights=move_weights, k=1)[0]

                    new_seq_A, new_seq_B, new_seq_C = curr_seq_A.copy(), curr_seq_B.copy(), curr_seq_C.copy()
                    new_orient = curr_orient.copy()

                    neighbor_generated = False
                    # Apply move
                    if self.n > 1: # Need at least 2 items to swap
                        if move_type == 1: # Swap in a single random sequence
                            seq_target_list = random.choice([new_seq_A, new_seq_B, new_seq_C])
                            i, j = random.sample(range(self.n), 2)
                            seq_target_list[i], seq_target_list[j] = seq_target_list[j], seq_target_list[i]
                            neighbor_generated = True
                        elif move_type == 2: # Swap in A and B
                            i, j = random.sample(range(self.n), 2)
                            new_seq_A[i], new_seq_A[j] = new_seq_A[j], new_seq_A[i]
                            new_seq_B[i], new_seq_B[j] = new_seq_B[j], new_seq_B[i]
                            neighbor_generated = True
                        elif move_type == 3: # Swap in A and C
                            i, j = random.sample(range(self.n), 2)
                            new_seq_A[i], new_seq_A[j] = new_seq_A[j], new_seq_A[i]
                            new_seq_C[i], new_seq_C[j] = new_seq_C[j], new_seq_C[i]
                            neighbor_generated = True
                        elif move_type == 4: # Swap in B and C
                            i, j = random.sample(range(self.n), 2)
                            new_seq_B[i], new_seq_B[j] = new_seq_B[j], new_seq_B[i]
                            new_seq_C[i], new_seq_C[j] = new_seq_C[j], new_seq_C[i]
                            neighbor_generated = True
                        elif move_type == 5: # Swap in all sequences (A, B, C)
                            i, j = random.sample(range(self.n), 2)
                            new_seq_A[i], new_seq_A[j] = new_seq_A[j], new_seq_A[i]
                            new_seq_B[i], new_seq_B[j] = new_seq_B[j], new_seq_B[i]
                            new_seq_C[i], new_seq_C[j] = new_seq_C[j], new_seq_C[i]
                            neighbor_generated = True

                    if move_type == 6 and self.n > 0: # Orientation change
                         box_id_to_rotate = random.choice(list(new_orient.keys()))
                         prod = self.products_dict[box_id_to_rotate]
                         current_ori = new_orient[box_id_to_rotate]

                         possible_new_oris = []
                         eps = 1e-5
                         if prod.get('upright_only', False):
                             # Valid orientations for upright are WHD and DHW (if they fit)
                             valid_upright = []
                             if prod['h'] <= self.H + eps:
                                 # WHD check
                                 if prod['w'] <= self.W + eps and prod['d'] <= self.D + eps: valid_upright.append("WHD")
                                 # DHW check
                                 if prod['d'] <= self.W + eps and prod['w'] <= self.D + eps: valid_upright.append("DHW")
                             possible_new_oris = [o for o in valid_upright if o != current_ori]
                         else:
                             # Regular product: find all valid orientations other than current one
                             all_oris = ["WHD", "WDH", "HWD", "HDW", "DHW", "DWH"]
                             for ori in all_oris:
                                 if ori == current_ori: continue
                                 w, h, d = self._rotate_dimensions(prod, ori)
                                 # Check if dimensions fit container
                                 if w <= self.W + eps and h <= self.H + eps and d <= self.D + eps:
                                     possible_new_oris.append(ori)

                         if possible_new_oris: # If there are other valid orientations
                             new_orient[box_id_to_rotate] = random.choice(possible_new_oris)
                             neighbor_generated = True

                    # --- End Neighbor Generation ---
                    if not neighbor_generated: continue # Skip if no change was made

                    # Evaluate new solution using the CORE _place_boxes
                    placement, new_util, valid = self._place_boxes(new_seq_A, new_seq_B, new_seq_C, new_orient)

                    if not valid: continue # Neighbor is invalid, generate another

                    # --- Acceptance Decision (Metropolis criterion) ---
                    accept = False
                    delta_util = new_util - curr_util

                    if delta_util > 0: # Always accept better solutions
                        accept = True
                    else: # Accept worse solutions with probability exp(delta/T)
                        # Avoid division by zero or math domain error with very small T
                        acceptance_prob = math.exp(delta_util / max(T, 1e-9))
                        if random.random() < acceptance_prob:
                            accept = True

                    if accept:
                        # Update current solution
                        curr_seq_A, curr_seq_B, curr_seq_C = new_seq_A, new_seq_B, new_seq_C
                        curr_orient = new_orient
                        curr_util = new_util
                        # Check if this accepted solution is the best found *so far* from this starting config
                        if new_util > best_config_util:
                            best_config_util = new_util
                            best_config_seq_A, best_config_seq_B, best_config_seq_C = new_seq_A.copy(), new_seq_B.copy(), new_seq_C.copy()
                            best_config_orient = new_orient.copy()
                            # Store the actual placement details corresponding to this best util
                            best_config_placement = placement

                    # Cool down temperature
                    T *= cooling_rate
                    iters_done += 1

                # --- End Simulated Annealing Loop ---
                if time.time() - start_time > time_limit_per_container: break # Check time limit again

                # After SA for a starting config, record the best result found *from that start*
                if best_config_util > best_attempt_util:
                     best_attempt_util = best_config_util
                     # Use the stored placement corresponding to best_config_util
                     best_attempt_placement = best_config_placement
                     # Store the sequences/orientations that produced this best result
                     best_attempt_config = {
                         "sequences": {"A": best_config_seq_A, "B": best_config_seq_B, "C": best_config_seq_C},
                         "orientations": best_config_orient
                     }

            # --- End Loop over Starting Configurations ---
            if time.time() - start_time > time_limit_per_container: break # Check time limit

            # After trying all start configs for this attempt, update overall best if needed
            if best_attempt_util > best_overall_util:
                found_valid_solution = True # Mark that we found at least one valid packing
                best_overall_util = best_attempt_util
                best_overall_placement = best_attempt_placement
                best_overall_config = best_attempt_config # Store the best config found across all attempts

        # --- End Attempts Loop ---

        # --- Return Result for this Container ---
        if found_valid_solution and best_overall_placement is not None:
             # Successfully found a valid packing for this container
            return {
                "container_index": container_index, "container_name": container_name,
                "container_volume": container_volume, "valid": True,
                "utilization": best_overall_util,
                "placement": best_overall_placement, # The list of placed item dicts
                "best_config": best_overall_config   # The sequences/orientations that achieved it
            }
        else:
            # No valid packing found within the constraints (time, iterations, attempts)
            msg = "No valid configuration found"
            if time.time() - start_time >= time_limit_per_container: msg += " (time limit reached)"
            # Check if it failed initial assessment too
            if definitely_too_small: msg = "Container too small based on quick assessment"
            elif total_weight > max_container_weight: msg = f"Total weight {total_weight:.2f} exceeds container limit {max_container_weight:.2f}"

            return {
                "container_index": container_index, "container_name": container_name,
                "container_volume": container_volume, "valid": False,
                "message": msg
            }


    def pack(self, products):
        """
        Pack products into the smallest possible container from the available list.

        Iterates through sorted containers, calling _optimize_for_container for each
        until a valid packing is found or all containers are tried. Manages time budget.

        Parameters:
        -----------
        products : list
            List of product dictionaries with 'id', 'w', 'h', 'd' and optional 'weight', 'upright_only'.

        Returns:
        --------
        dict
            Packing result: {'container': {...}, 'placements': [...]} if successful,
            or {'error': 'message'} if packing fails.
        """
        if not products: return {"error": "No products provided"}
        if not self.containers: return {"error": "No containers available"}

        # Ensure unique IDs (essential for lookups in products_dict)
        product_ids = set()
        ids_ok = True
        for i, p in enumerate(products):
            p_id = p.get('id')
            if p_id is None or p_id in product_ids:
                # print(f"Warning: Product ID missing or duplicaeted for product at index {i}. Assigning temporary ID 'temp_prod_{i}'.")
                p['id'] = f"temp_prod_{i}"
                if p_id in product_ids: ids_ok=False # Mark duplication occurred
            product_ids.add(p['id'])
        # if not ids_ok: print("Warning: Duplicate product IDs were detected and replaced.")

        # Store products and dict for easy access during optimization
        self.products = products
        self.n = len(products)
        self.products_dict = {prod['id']: prod for prod in products}

        # --- Fast path for a single product ---
        if self.n == 1:
            product = products[0]
            product_weight = product.get('weight', 0.0)
            product_volume = product['w'] * product['h'] * product['d']
            epsilon = 1e-5

            for idx, container in enumerate(self.containers):
                container_volume = container['W'] * container['H'] * container['D']
                max_weight = container.get('max_weight', float('inf'))

                # Check weight constraint first
                if product_weight > max_weight: continue

                found_orientation = None
                placement_dims = {}

                possible_orientations = []
                if product.get('upright_only', False):
                    # Only check WHD and DHW orientations for upright items
                    if product['h'] <= container['H'] + epsilon:
                        if product['w'] <= container['W'] + epsilon and product['d'] <= container['D'] + epsilon:
                             possible_orientations.append("WHD")
                        if product['d'] <= container['W'] + epsilon and product['w'] <= container['D'] + epsilon:
                             possible_orientations.append("DHW")
                else:
                    # Check all 6 orientations for regular items
                    all_oris = ["WHD", "WDH", "HWD", "HDW", "DHW", "DWH"]
                    for ori in all_oris:
                        w, h, d = self._rotate_dimensions(product, ori)
                        if w <= container['W'] + epsilon and h <= container['H'] + epsilon and d <= container['D'] + epsilon:
                            possible_orientations.append(ori)

                # Choose the first valid orientation found (smallest container is already prioritized)
                if possible_orientations:
                    found_orientation = possible_orientations[0]
                    w_place, h_place, d_place = self._rotate_dimensions(product, found_orientation)
                    placement_dims = {'w': w_place, 'h': h_place, 'd': d_place}

                    # If an orientation fits, pack it into this container
                    return {
                        "container": {
                            "name": container.get('name', f'Container-{idx}'),
                            "width": container['W'], "height": container['H'], "depth": container['D'],
                            "max_weight": container.get('max_weight'),
                            "utilization": product_volume / container_volume if container_volume > 0 else 0
                        },
                        "placements": [{
                            "id": product['id'], "x": 0, "y": 0, "z": 0, # Place at origin
                            "w": placement_dims['w'], "h": placement_dims['h'], "d": placement_dims['d'],
                            "orientation": found_orientation,
                            "weight": product_weight
                        }]
                    }
            # If loop finishes, no container fits the single product
            return {"error": "No suitable container found for the single product (dimensions or weight)"}

        # --- Standard Optimization Loop for Multiple Products ---
        successful_result = None
        successful_container = None
        total_time_budget = self.time_limit # Use the instance's overall time limit
        start_time_packing = time.time()

        # Iterate through containers (sorted smallest to largest)
        for idx, container in enumerate(self.containers):
            current_elapsed_time = time.time() - start_time_packing
            if current_elapsed_time > total_time_budget:
                print(f"Total packing time limit ({total_time_budget:.2f}s) exceeded before trying container {idx+1}.")
                break # Stop trying containers if overall time limit is reached

            # Allocate remaining time somewhat proportionally to remaining containers
            # This is a simple strategy; more complex ones could prioritize smaller containers more
            remaining_total_time = max(0, total_time_budget - current_elapsed_time)
            remaining_containers_count = max(1, len(self.containers) - idx)
            time_for_this_container = remaining_total_time / remaining_containers_count

            # Store the allocated time where _optimize_for_container can access it
            # (Using an instance variable for simplicity, though passing as arg is cleaner)
            self.current_container_time_limit = time_for_this_container

            # --- Call the optimization for this specific container ---
            result = self._optimize_for_container(self.products, container, idx)

            if result.get("valid"):
                # Found the first (smallest) container that works
                successful_result = result
                successful_container = container
                break 

        # --- Format and Return Final Result ---
        if successful_result and successful_container:
            # Add weight information to the final placement list
            final_placements = successful_result.get("placement", [])
            total_packed_weight = 0
            for p in final_placements:
                product_id = p.get("id")
                # Safely get weight from the original product data
                p['weight'] = self.products_dict.get(product_id, {}).get('weight', 0.0)
                total_packed_weight += p['weight']

            return {
                "container": {
                    "name": successful_result["container_name"],
                    "width": successful_container["W"],
                    "height": successful_container["H"],
                    "depth": successful_container["D"],
                    "max_weight": successful_container.get('max_weight'),
                    "volume": successful_container["W"] * successful_container["H"] * successful_container["D"],
                    "utilization_volume": successful_result.get("utilization", 0.0),
                    "packed_weight": total_packed_weight,
                },
                "placements": final_placements
            }
        else:
            # Went through all containers (or timed out) and found no solution
            error_msg = "No suitable container found for the given products."
            if time.time() - start_time_packing >= total_time_budget:
                 error_msg += " (Overall time limit reached)"
            return {"error": error_msg}