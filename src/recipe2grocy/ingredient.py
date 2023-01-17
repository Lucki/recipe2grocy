class Ingredient():
    def __init__(self, config, host, debug) -> None:
        self.__config = config
        self.__debug = debug
        self.__host = host
        self.__name = None
        self.__note = ""
        self.__only_single_unit = "0"
        self.__unit = None
        self.__variable_amount = ""

    def __get_amount(self, amount):
        if self.__host in self.__config and \
            "amounts" in self.__config[self.__host] and \
                amount in self.__config[self.__host]["amounts"]:
            return self.__config[self.__host]["amounts"][amount]

        if "default" in self.__config and \
            "amounts" in self.__config["default"] and \
                amount in self.__config["default"]["amounts"]:
            return self.__config["default"]["amounts"][amount]

        return None

    def __get_factor(self, unit):
        if self.__name is not None and \
            self.__host in self.__config and \
            "products" in self.__config[self.__host] and \
            self.__name in self.__config[self.__host]["products"] and \
                "factor" in self.__config[self.__host]["products"][self.__name]:
            # Overridden by product
            return self.__config[self.__host]["products"][self.__name]["factor"]

        if self.__name is not None and \
            "default" in self.__config and \
            "products" in self.__config["default"] and \
            self.__name in self.__config["default"]["products"] and \
                "factor" in self.__config["default"]["products"][self.__name]:
            # Overridden by product
            return self.__config["default"]["products"][self.__name]["factor"]

        if unit is not None and \
            self.__host in self.__config and \
            "units" in self.__config[self.__host] and \
            unit in self.__config[self.__host]["units"] and \
                "factor" in self.__config[self.__host]["units"][unit]:
            return self.__config[self.__host]["units"][unit]["factor"]

        if unit is not None and \
            "default" in self.__config and \
            "units" in self.__config["default"] and \
            unit in self.__config["default"]["units"] and \
                "factor" in self.__config["default"]["units"][unit]:
            return self.__config["default"]["units"][unit]["factor"]

        return None

    def __get_modifier(self, modifier):
        if self.__host in self.__config and \
            "modifiers" in self.__config[self.__host] and \
                modifier in self.__config[self.__host]["modifiers"]:
            return modifier

        if "default" in self.__config and \
            "modifiers" in self.__config["default"] and \
                modifier in self.__config["default"]["modifiers"]:
            return modifier

        return None

    def __get_name(self, product):
        if self.__host in self.__config and \
            "products" in self.__config[self.__host] and \
            product in self.__config[self.__host]["products"] and \
                "name" in self.__config[self.__host]["products"][product]:
            return self.__config[self.__host]["products"][product]["name"]

        if "default" in self.__config and \
            "products" in self.__config["default"] and \
            product in self.__config["default"]["products"] and \
                "name" in self.__config["default"]["products"][product]:
            return self.__config["default"]["products"][product]["name"]

        return None

    def __get_unit(self, unit):
        if self.__name is not None and \
            self.__host in self.__config and \
            "products" in self.__config[self.__host] and \
            self.__name in self.__config[self.__host]["products"] and \
                "unit" in self.__config[self.__host]["products"][self.__name]:
            # Overridden by product
            return self.__config[self.__host]["products"][self.__name]["unit"]

        if self.__name is not None and \
            "default" in self.__config and \
            "products" in self.__config["default"] and \
            self.__name in self.__config["default"]["products"] and \
                "unit" in self.__config["default"]["products"][self.__name]:
            # Overridden by product
            return self.__config["default"]["products"][self.__name]["unit"]

        if self.__host in self.__config and \
            "units" in self.__config[self.__host] and \
            unit in self.__config[self.__host]["units"] and \
                "name" in self.__config[self.__host]["units"][unit]:
            return self.__config[self.__host]["units"][unit]["name"]

        if "default" in self.__config and \
            "units" in self.__config["default"] and \
            unit in self.__config["default"]["units"] and \
                "name" in self.__config["default"]["units"][unit]:
            return self.__config["default"]["units"][unit]["name"]

        return None

    def __disambiguate(self):
        if self.__host in self.__config and \
           "disambiguate" in self.__config[self.__host] and \
           self.__name in self.__config[self.__host]["disambiguate"] and \
           self.__unit in self.__config[self.__host]["disambiguate"][self.__name]:
            self.__name = self.__config[self.__host]["disambiguate"][self.__name][self.__unit]
            return

        if "default" in self.__config and \
           "disambiguate" in self.__config["default"] and \
           self.__name in self.__config["default"]["disambiguate"] and \
                self.__unit in self.__config["default"]["disambiguate"][self.__name]:
            self.__name = self.__config["deafult"]["disambiguate"][self.__name][self.__unit]
            return

    def __get_default_unit(self):
        if self.__host in self.__config and \
                "default_unit" in self.__config[self.__host]:
            return self.__config[self.__host]["default_unit"]

        if "default" in self.__config and \
                "default_unit" in self.__config["default"]:
            return self.__config["default"]["default_unit"]

        return None

    def amount(self):
        return self.__amount

    def check_single(self):
        return self.__only_single_unit

    def id(self):
        return self.__id

    def name(self):
        return self.__name

    def note(self):
        return self.__note

    def unit(self):
        return self.__unit

    def variable_amount(self):
        return self.__variable_amount

    def set_amount(self, amount):
        self.__amount = amount

    def set_id(self, id):
        self.__id = id

    def parse_ingredient(self, ingredient):
        # Encountered combinations
        # Amount    modifier    Unit    Product                     , Note
        #                               Salz und Pfeffer
        #                               Kräuter                     , italienische
        # 3                     Prisen  Pfeffer
        # 1                             Zwiebel (ca. 50 g)          , halbiert
        # 200                   g       Staudensellerie             , in Würfeln (1 cm)
        # 2         geh.        TL      Gewürzpaste für Gemüsebrühe , selbst gemacht oder 2 Würfel Gemüsebrühe(für 0,5 l)

        amounts = []
        modifier = None
        original_unit = self.__get_default_unit()
        product = ""

        if self.__debug:
            print(f"raw: '{ingredient}'")

        # FIXME: 0,5 l will fail
        splitted_ingredient = ingredient.split(',', 1)

        if len(splitted_ingredient) > 1:
            self.__note = splitted_ingredient[1].strip()

        # Dump something like this into notes: "Zwiebel (ca. 50 g)"
        splitted_ingredient = splitted_ingredient[0].split(" (", 1)

        if len(splitted_ingredient) > 1:
            self.__note = f"{self.__note} ({splitted_ingredient[1]}"

        splitted_ingredient = splitted_ingredient[0].split(' ')

        try:
            float(splitted_ingredient[0])
        except ValueError:
            self.__only_single_unit = "1"

        if len(splitted_ingredient) < 1:
            print("Something went wrong")
            return

        amount = self.__get_amount(splitted_ingredient[0])
        if amount is not None:
            amounts.append(float(amount))
        elif self.__only_single_unit == "1":
            amounts.append(0)
        else:
            amounts.append(float(splitted_ingredient[0]))

        for i in range(0, len(splitted_ingredient)):
            if i == 0 and self.__only_single_unit == "0":
                continue

            # Catch something like "1 ½"
            amount = self.__get_amount(splitted_ingredient[i])
            if amount is not None:
                amounts.append(amount)
                continue

            modifier = self.__get_modifier(splitted_ingredient[i])
            if modifier is not None:
                if self.__only_single_unit == "1":
                    self.__variable_amount = modifier
                else:
                    self.__note = f"{modifier}, {self.__note}"
                continue

            # We don't know the product name yet
            unit = self.__get_unit(splitted_ingredient[i])
            if unit is not None:
                unit = None
                original_unit = splitted_ingredient[i]
                continue

            product = f"{product} {splitted_ingredient[i]}"

        product = product.strip()

        self.__name = self.__get_name(product)
        if self.__name is None:
            self.__name = product

        # Recheck unit with known product
        self.__unit = self.__get_unit(original_unit)

        if self.__unit is None:
            self.__unit = original_unit

        # Using new product and the unconverted unit here
        factor = self.__get_factor(original_unit)

        self.__amount = 0
        for value in amounts:
            self.__amount += float(value)

        if factor is not None:
            self.__amount = self.__amount * factor

        self.__disambiguate()

        if self.__debug:
            print(f"Amount: '{self.__amount}'")
            print(f"Unit: '{self.__unit}'")
            print(f"Product: {self.__name}")
            print(f"Note: '{self.__note}'")
