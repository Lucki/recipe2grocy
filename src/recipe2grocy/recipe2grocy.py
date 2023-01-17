import argparse
import os
import pygrocy
import tomlkit
import sys
from appdirs import *
from recipe_scrapers import scrape_me
from recipe_scrapers import scrape_html
from texttable import Texttable

from ingredient import Ingredient


def is_product_ignored(config, host, name):
    if host in config and \
       "ignored_products" in config[host] and \
       name in config[host]["ignored_products"]:
        return True

    if "default" in config and \
       "ignored_products" in config["default"] and \
       name in config["default"]["ignored_products"]:
        return True

    return False


argparser = argparse.ArgumentParser(
    description="Convert and insert recipes into Grocy."
)

argparser.add_argument(
    "--url",
    help="The URL to scrape or the URL where the html file (--input) originated from.",
    required=True,
)
argparser.add_argument(
    "--input",
    help="FILE containing the HTML",
    metavar="FILE",
    nargs="?",
)
argparser.add_argument(
    "--debug",
    help="Print additional debug information",
    action="store_true",
    default=False,
)
argparser.add_argument(
    "--no-confirm",
    help="Don't ask for confirmation before adding the recipe",
    action="store_true",
    default=False,
)

args = argparser.parse_args()

if args.input is not None:
    with open(args.input, "r") as file:
        scraper = scrape_html(file.read(), args.url)
else:
    scraper = scrape_me(args.url)

try:
    if scraper.instructions() == "":
        print("Instructions empty")
        sys.exit(1)
except AttributeError as e:
    print(f"Error: {e}")
    sys.exit(1)

appname = "Recipe2Grocy"
config_dir = user_config_dir(appname)

with open(os.path.join(config_dir, "conversions.toml"), "r") as file:
    config = tomlkit.parse(file.read())

grocy = pygrocy.Grocy(
    config["grocy_url"] if "grocy_url" in config else "http://localhost",
    str(config["api_key"]),  # windows needs str() here
    config["api_port"] if "api_port" in config else pygrocy.grocy.DEFAULT_PORT_NUMBER,
    debug=args.debug,
)

existing_recipes = grocy.get_generic_objects_for_type(
    pygrocy.EntityType.RECIPES,
    query_filters=[
        f"name={scraper.title()}",
    ],
)

if len(existing_recipes) > 1:
    if not args.no_confirm:
        print("Recipe with same name already exists")

        answer = input("Add new recipe anyway? (Y/n)")
        if answer.lower() != "y" and answer != "":
            sys.exit(0)

ingredients = []

for ingredient_string in scraper.ingredients():
    ingredient = Ingredient(config, scraper.host(), args.debug)
    ingredient.parse_ingredient(ingredient_string)

    if is_product_ignored(config, scraper.host(), ingredient.name()):
        if args.debug:
            print(f"Ignoring \"{ingredient.name()}\"")
        continue

    ingredients.append(ingredient)

missing_grocy_conversions = {}
missing_grocy_ingredients = []
missing_grocy_units = []
for ingredient in ingredients:
    existing_products = grocy.get_generic_objects_for_type(
        pygrocy.EntityType.PRODUCTS,
        query_filters=[
            f"name={ingredient.name()}",
        ],
    )

    if len(existing_products) < 1:
        if args.debug:
            print(f"Product missing: '{ingredient.name()}'")
        missing_grocy_ingredients.append(ingredient.name())
        continue

    if len(existing_products) > 1:
        print("This shouldn't happen")
        sys.exit(1)

    ingredient.set_id(existing_products[0]["id"])

    unit = grocy.get_generic_objects_for_type(
        pygrocy.EntityType.QUANTITY_UNITS,
        [
            f"name={ingredient.unit()}",
        ],
    )

    if len(unit) < 1:
        unit = grocy.get_generic_objects_for_type(
            pygrocy.EntityType.QUANTITY_UNITS,
            [
                f"name_plural={ingredient.unit()}",
            ],
        )

    if len(unit) < 1:
        if args.debug:
            print(f"Unit \"{ingredient.unit()}\" not found")
        missing_grocy_units.append(ingredient.unit())
        continue

    if len(unit) > 1:
        print("This shouldn't happen2")
        sys.exit(1)

    if unit[0]["id"] != existing_products[0]["qu_id_stock"]:
        conversions = grocy.get_generic_objects_for_type(
            pygrocy.EntityType.QUANTITY_UNIT_CONVERSIONS,
            [
                f"product_id={ingredient.id()}",
                f"from_qu_id={unit[0]['id']}",
                f"to_qu_id={existing_products[0]['qu_id_stock']}",
            ],
        )

        if len(conversions) < 1:
            # retry without product
            conversions = grocy.get_generic_objects_for_type(
                pygrocy.EntityType.QUANTITY_UNIT_CONVERSIONS,
                [
                    "product_id=''",
                    f"from_qu_id={unit[0]['id']}",
                    f"to_qu_id={existing_products[0]['qu_id_stock']}",
                ],
            )

            if len(conversions) < 1:
                missing_grocy_conversions[ingredient.name()
                                          ] = ingredient.unit()
                continue

        if len(conversions) > 1:
            print("This shouldn't happen3")
            sys.exit(1)

        ingredient.set_amount(str(
            float(ingredient.amount()) * conversions[0]["factor"]))
        if args.debug:
            print(f"Amount: {ingredient.amount()}")

if len(missing_grocy_ingredients) > 0:
    print("==> Please add the following products to your Grocy instance or map them to a different product using the config file.")
    print("==> If there are unwanted parts in the product name then make sure those parts are correctly mapped to units or modifiers in the config file.")
    print(*missing_grocy_ingredients, sep='\n')

if len(missing_grocy_units) > 0:
    print("==> Please add the following units to your Grocy instance or map them to a different unit using the config file.")
    print(*missing_grocy_units, sep='\n')

if len(missing_grocy_conversions) > 0:
    print("==> Please add the following conversion rates to your Grocy instance (per product or global) or remap them using the config file.")
    for n, u in missing_grocy_conversions.items():
        print(f"'{u}' → stock unit of '{n}'")

if len(missing_grocy_ingredients) > 0 or len(missing_grocy_conversions) > 0 or len(missing_grocy_units) > 0:
    sys.exit(1)

instructions = "<p>" + scraper.instructions().replace('\n', '</p><p>') + "</p>"

if not args.no_confirm:
    table = Texttable()
    table.add_row(["Quantity", "Unit", "Product", "Note"])

    for ingredient in ingredients:
        table.add_row([ingredient.amount(), ingredient.unit(),
                      ingredient.name(), ingredient.note()])

    print(table.draw())
    answer = input("Add recipe to grocy? (Y/n)")
    if answer.lower() != "y" and answer != "":
        sys.exit(0)

# "{\"name\":\"Testrezept\",\"base_servings\":\"4\",\"product_id\":\"119\",\"description\":\"<p>asdasd</p><p>asdasd<br></p><p>asdasd<br></p>\",\"not_check_shoppinglist\":\"0\"}"
recipe = grocy.add_generic(pygrocy.EntityType.RECIPES, {
    "name": scraper.title(),
    "base_servings": scraper.yields().split()[0],  # Hopefully this will work
    # "product_id": "" ?
    "description": instructions,
    "not_check_shoppinglist": "0",
})

for ingredient in ingredients:
    # {\"product_id\":\"119\",\"amount\":\"2.\",\"variable_amount\":\"\",\"ingredient_group\":\"Obst\",\"note\":\"notes\",\"price_factor\":\"1\",\"only_check_single_unit_in_stock\":\"0\",\"not_check_stock_fulfillment\":\"0\",\"recipe_id\":3}
    id = grocy.add_generic(pygrocy.EntityType.RECIPES_POS, {
        "recipe_id": recipe["created_object_id"],
        "product_id": ingredient.id(),
        "amount": ingredient.amount(),
        "note": ingredient.note(),
        "only_check_single_unit_in_stock": ingredient.check_single(),
        "variable_amount": ingredient.variable_amount(),
    })
