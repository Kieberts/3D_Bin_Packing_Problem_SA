import random
import math

class SimulatedAnnealingPackerV1:
    def __init__(self, container_width, container_height, container_depth, beta=0.2, alpha=0.002, initial_temperature=0.2, max_iter=10000):
        """
        Initialisiert den Container-Packer für Version 1 (Mostaghimi et al.).
        :param container_width, container_height, container_depth: Abmessungen des Containers.
        :param beta: Kühlungs-Parameter β für Temperaturverringerung bei Annahme.
        :param alpha: Heizungs-Parameter α für Temperaturerhöhung bei Ablehnung.
        :param initial_temperature: Start-Temperatur.
        :param max_iter: Maximale Anzahl Iterationen der SA-Schleife.
        """
        self.W = container_width
        self.H = container_height
        self.D = container_depth
        self.beta = beta
        self.alpha = alpha
        self.initial_temperature = initial_temperature
        self.max_iter = max_iter

    def _rotate_dimensions(self, box, orientation):
        """
        Gibt die (Breite, Höhe, Tiefe) einer Box für die gegebene Orientierung zurück.
        orientation ist ein String aus {"WHD","WDH","HWD","HDW","DHW","DWH"}.
        box ist ein Dict mit Originaldimensionen 'w','h','d'.
        """
        w, h, d = box['w'], box['h'], box['d']
        if orientation == "WHD":
            # Standard: (Width, Height, Depth) unverändert
            return w, h, d
        elif orientation == "WDH":
            # Swap Height und Depth
            return w, d, h
        elif orientation == "HWD":
            # Swap Width und Height
            return h, w, d
        elif orientation == "HDW":
            # Swap Width und Height, dann Height und Depth
            # Nach erstem Swap: (h, w, d), dann Height<->Depth => (h, d, w)
            return h, d, w
        elif orientation == "DHW":
            # Swap Depth und Width
            return d, h, w
        elif orientation == "DWH":
            # Swap Depth und Width, dann Depth und Height
            # Nach erstem Swap: (d, h, w), dann Height<->Depth => (d, w, h)
            return d, w, h

    def _place_boxes(self, sequence_A, sequence_B, sequence_C, orientations):
        """
        Platziert die Boxen gemäß der gegebenen Sequenzen (A, B, C) und Orientierungen.
        Berechnet Koordinaten (x,y,z) jeder Box und prüft auf Kollision/Überschreitung.
        Returns: (placement_list, utilization, valid)
         - placement_list: Liste von Dicts mit 'id','x','y','z','orientation','w','h','d'
         - utilization: genutzter Volumenanteil (0-1)
         - valid: Bool, True wenn alle Boxen im Container liegen (keine Überschreitung).
        """
        n = len(sequence_B)  # B-Sequenz gibt Reihenfolge des Einfügens
        placed = {}  # gespeicherte Platzierungen: id -> (x,y,z,w,h,d)
        # Hilfsfunktionen um anhand Sequence zu prüfen, ob j vor i in A, B oder C kommt.
        # Wir speichern die Position jeder Box in jeder Sequenz für schnellen Zugriff.
        pos_in_A = {seq_id: idx for idx, seq_id in enumerate(sequence_A)}
        pos_in_B = {seq_id: idx for idx, seq_id in enumerate(sequence_B)}
        pos_in_C = {seq_id: idx for idx, seq_id in enumerate(sequence_C)}

        placement_list = []  # Ergebnis-Liste der Platzierungen
        total_volume = 0

        for box_id in sequence_B:  # iteriere in Einfüge-Reihenfolge B
            box = self.products_dict[box_id]
            ori = orientations[box_id]
            # Drehung der Box gemäß Orientierungsvektor
            w, h, d = self._rotate_dimensions(box, ori)
            # Anfangskoordinaten berechnen nach Formel:
            # x_i = max(0, max_{j in P_x}(x_j + w_j)), analog y_i, z_i.
            x_i = 0
            y_i = 0
            z_i = 0
            # P_x: bereits platzierte Boxen, die in A vor der aktuellen Box kommen (d.h. links von aktueller Box liegen sollten).
            # Prüfe alle j in placed, ob pos_in_A[j] < pos_in_A[i]
            for j, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                if pos_in_A[j] < pos_in_A[box_id]:
                    # j soll links/oben/vorne von i liegen => i muss rechts/hinten/unten von j liegen,
                    # daher j "links" von i im Sinne der x-Koordinate:
                    x_i = max(x_i, x_j + w_j)
            # P_y: Boxen, die in B vor aktueller Box kommen (also B-Sequenz früher -> sollen unter i liegen).
            for j, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                if pos_in_B[j] < pos_in_B[box_id]:
                    # j liegt in B vor i -> j soll unter/links/hinter i sein => j möglicherweise unter i
                    y_i = max(y_i, y_j + h_j)
            # P_z: Boxen, die in C vor aktueller Box kommen (sollen hinter i liegen).
            for j, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                if pos_in_C[j] < pos_in_C[box_id]:
                    # j in C vor i -> j soll hinter/unter/vor i sein => j möglicherweise hinter i (also weiter hinten im Container)
                    z_i = max(z_i, z_j + d_j)

            # Jetzt vertikaler Stabilitäts-Check: Box ggf. absenken, wenn eine Ecke auf einer Box darunter aufsetzen kann.
            # Wir prüfen die vier Ecken der Box-Unterseite und suchen nach vorhandenem "Unterbau".
            supported_y = None  # die neue y-Position, falls eine Ecke aufstützt
            # 1. Ecke: vorne-links (x_i, z_i)
            for j, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                if (x_j <= x_i <= x_j + w_j - 1) and (z_j <= z_i <= z_j + d_j - 1):
                    # Die vordere linke Ecke liegt über Box j
                    supported_y = y_j + h_j
                    break
            if supported_y is None:
                # 2. Ecke: vorne-rechts (x_i + w, z_i)
                corner_x = x_i + w
                corner_z = z_i
                for j, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                    if (x_j <= corner_x <= x_j + w_j) and (z_j <= corner_z <= z_j + d_j - 1):
                        supported_y = y_j + h_j
                        break
            if supported_y is None:
                # 3. Ecke: hinten-links (x_i, z_i + d)
                corner_x = x_i
                corner_z = z_i + d
                for j, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                    if (x_j <= corner_x <= x_j + w_j - 1) and (z_j <= corner_z <= z_j + d_j):
                        supported_y = y_j + h_j
                        break
            if supported_y is None:
                # 4. Ecke: hinten-rechts (x_i + w, z_i + d)
                corner_x = x_i + w
                corner_z = z_i + d
                for j, (x_j, y_j, z_j, w_j, h_j, d_j) in placed.items():
                    if (x_j <= corner_x <= x_j + w_j) and (z_j <= corner_z <= z_j + d_j):
                        supported_y = y_j + h_j
                        break
            if supported_y is not None:
                # Eine Ecke hat Unterstützung gefunden -> Box auf diese Höhe setzen
                if supported_y > y_i:
                    y_i = supported_y

            # Platzierung prüfen: passt Box innerhalb des Containers?
            if x_i + w > self.W or y_i + h > self.H or z_i + d > self.D:
                # Überschreitet Containermaß, Abbruch
                return None, 0.0, False

            # Box i an (x_i, y_i, z_i) platzieren
            placed[box_id] = (x_i, y_i, z_i, w, h, d)
            total_volume += w * h * d
            placement_list.append({
                "id": box_id,
                "x": x_i, "y": y_i, "z": z_i,
                "w": w, "h": h, "d": d,
                "orientation": ori
            })

        utilization = total_volume / float(self.W * self.H * self.D)
        return placement_list, utilization, True

    def pack(self, products):
        """
        Führt den Simulated Annealing Packalgorithmus aus.
        :param products: Liste von Produkt-Dictionaries mit 'id','w','h','d' (Abmessungen).
        :return: Ergebnisdict mit Container und Packliste.
        """
        # Eingabe abspeichern und vorbereiten
        self.products = products
        self.n = len(products)
        # Mapping von Produkt-ID zu Produktdaten für schnellen Zugriff
        self.products_dict = {prod['id']: {'w': prod['w'], 'h': prod['h'], 'd': prod['d']} for prod in products}

        # Initialisiere Sequence Triple und Orientierungen
        # Wir nutzen z.B. als Startheuristik: B-Sequenz sortiert nach Volumen absteigend (First Fit Decreasing nach Volumen)
        # und A, C Sequenzen identisch zur B-Sequenz (ein einfacher, konsistenter Start).
        # Alternativ könnte man alle drei zufällig wählen, sofern konsistent.
        products_sorted = sorted(products, key=lambda p: p['w'] * p['h'] * p['d'], reverse=True)
        sequence_B = [p['id'] for p in products_sorted]
        # Wähle A und C hier der Einfachheit halber gleich B (andere Wahl wäre random Permutation oder sortiert nach anderer Eigenschaft)
        sequence_A = sequence_B.copy()
        sequence_C = sequence_B.copy()

        # Initiale Orientierungen zufällig wählen für jede Box
        orientation_options = ["WHD", "WDH", "HWD", "HDW", "DHW", "DWH"]
        orientations = {p['id']: random.choice(orientation_options) for p in products}

        # Berechne anfängliche Platzierung und Auslastung
        placement, best_util, valid = self._place_boxes(sequence_A, sequence_B, sequence_C, orientations)
        if not valid:
            # Falls initiale Lösung ungültig (Boxen passen nicht), kann man hier ggf. andere Startsequenz versuchen.
            # Wir brechen ab, da Packen in gegebenem Container nicht möglich scheint.
            return {"error": "Initial packing did not fit in container."}

        best_sequence_A = sequence_A[:]
        best_sequence_B = sequence_B[:]
        best_sequence_C = sequence_C[:]
        best_orientations = orientations.copy()

        # Aktuelle Lösung initialisieren
        curr_sequence_A = sequence_A[:]
        curr_sequence_B = sequence_B[:]
        curr_sequence_C = sequence_C[:]
        curr_orientations = orientations.copy()
        curr_util = best_util

        # Simulated Annealing Iterationsschleife
        T = self.initial_temperature

        for it in range(self.max_iter):
            # Nachbarschaft erzeugen
            # Wir wählen zufällig einen der 6 Moves (5 Permutations-Typen + 1 Orientierungsänderung)
            move_type = random.randint(1, 6)
            # Kopien der aktuellen Sequenzen und Orientierungen erzeugen
            new_seq_A = curr_sequence_A[:]
            new_seq_B = curr_sequence_B[:]
            new_seq_C = curr_sequence_C[:]
            new_orientations = curr_orientations.copy()

            if move_type == 1:
                # Tausch in einer einzelnen Sequenz (A oder B oder C zufällig wählen)
                seq_choice = random.choice(['A', 'B', 'C'])
                if seq_choice == 'A':
                    i, j = random.sample(range(self.n), 2)
                    new_seq_A[i], new_seq_A[j] = new_seq_A[j], new_seq_A[i]
                elif seq_choice == 'B':
                    i, j = random.sample(range(self.n), 2)
                    new_seq_B[i], new_seq_B[j] = new_seq_B[j], new_seq_B[i]
                elif seq_choice == 'C':
                    i, j = random.sample(range(self.n), 2)
                    new_seq_C[i], new_seq_C[j] = new_seq_C[j], new_seq_C[i]
            elif move_type == 2:
                # Tausch in A und B
                i, j = random.sample(range(self.n), 2)
                # finde die tatsächlichen Box-IDs an Position i und j in A (und entsprechend in B)
                idA_i, idA_j = new_seq_A[i], new_seq_A[j]
                idB_i, idB_j = new_seq_B[i], new_seq_B[j]
                # tausche die jeweiligen Elemente
                new_seq_A[i], new_seq_A[j] = idA_j, idA_i
                new_seq_B[i], new_seq_B[j] = idB_j, idB_i
            elif move_type == 3:
                # Tausch in A und C
                i, j = random.sample(range(self.n), 2)
                idA_i, idA_j = new_seq_A[i], new_seq_A[j]
                idC_i, idC_j = new_seq_C[i], new_seq_C[j]
                new_seq_A[i], new_seq_A[j] = idA_j, idA_i
                new_seq_C[i], new_seq_C[j] = idC_j, idC_i
            elif move_type == 4:
                # Tausch in B und C
                i, j = random.sample(range(self.n), 2)
                idB_i, idB_j = new_seq_B[i], new_seq_B[j]
                idC_i, idC_j = new_seq_C[i], new_seq_C[j]
                new_seq_B[i], new_seq_B[j] = idB_j, idB_i
                new_seq_C[i], new_seq_C[j] = idC_j, idC_i
            elif move_type == 5:
                # Tausch in allen drei Sequenzen (Box an Position i mit Box an Position j komplett vertauschen)
                i, j = random.sample(range(self.n), 2)
                idA_i, idA_j = new_seq_A[i], new_seq_A[j]
                idB_i, idB_j = new_seq_B[i], new_seq_B[j]
                idC_i, idC_j = new_seq_C[i], new_seq_C[j]
                # Hier nehmen wir an, dass die gleichen Indizes i,j in allen Sequenzen referenzieren dasselbe Boxenpaar
                # (Das Triple repräsentiert dieselbe Box an jeweiliger Position in allen Sequenzen in konsistenter Weise.)
                new_seq_A[i], new_seq_A[j] = idA_j, idA_i
                new_seq_B[i], new_seq_B[j] = idB_j, idB_i
                new_seq_C[i], new_seq_C[j] = idC_j, idC_i
            else:
                # move_type == 6: Rotationsänderung einer Box
                box_id = random.choice(list(new_orientations.keys()))
                # zufällige andere Orientierung wählen
                current_ori = new_orientations[box_id]
                other_oris = [ori for ori in orientation_options if ori != current_ori]
                new_orientations[box_id] = random.choice(other_oris)

            # Neue Lösung bewerten (platzieren und Auslastung berechnen)
            placement, new_util, valid = self._place_boxes(new_seq_A, new_seq_B, new_seq_C, new_orientations)
            if not valid:
                # Ungültige Nachbarschaft (eine Box passt nicht rein oder Überlappung - sollte eigtl. nicht passieren, außer Container zu klein)
                # -> überspringe diese Iteration ohne Änderung
                continue

            # Entscheide über Annahme nach Metropolis-Kriterium
            accept = False
            if new_util > curr_util:
                accept = True
            else:
                # Schlechtere Lösung: mit Wahrscheinlichkeit exp((new_util-curr_util)/T)
                delta = new_util - curr_util
                if random.random() < math.exp(delta / T):
                    accept = True

            if accept:
                # Lösung übernehmen
                curr_sequence_A = new_seq_A
                curr_sequence_B = new_seq_B
                curr_sequence_C = new_seq_C
                curr_orientations = new_orientations
                curr_util = new_util
                # Temperatur absenken (cooling)
                T = T / (1 + self.beta * T)
                # Ist die neue Lösung zugleich die beste bisher?
                if new_util > best_util:
                    best_util = new_util
                    best_sequence_A = new_seq_A[:]
                    best_sequence_B = new_seq_B[:]
                    best_sequence_C = new_seq_C[:]
                    best_orientations = new_orientations.copy()
            else:
                # Schlechtere Lösung abgelehnt -> Temperatur leicht erhöhen (heating)
                T = T / (1 - self.alpha * T)

            # Optional: Abbruch, wenn Temperatur sehr niedrig (nahe 0) oder kaum Veränderung
            if T < 1e-6:
                break

        # Nach SA: best_sequence_* und best_orientations sind das Ergebnis
        best_placement, best_util, valid = self._place_boxes(best_sequence_A, best_sequence_B, best_sequence_C, best_orientations)
        result = {
            "container": {
                "width": self.W,
                "height": self.H,
                "depth": self.D,
                "utilization": best_util
            },
            "placements": best_placement
        }
        return result
