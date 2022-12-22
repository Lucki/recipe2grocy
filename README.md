# Recipe2Grocy

Moves scraped recipes into Grocy.

```
usage: recipe2grocy.py [-h] --url URL [--input [FILE]] [--debug] [--no-confirm]

Convert and insert recipes into Grocy.

options:
  -h, --help      show this help message and exit
  --url URL       The URL to scrape or the URL where the html file (--input) originated from.
  --input [FILE]  FILE containing the HTML
  --debug         Print additional debug information
  --no-confirm    Don't ask for confirmation before adding the recipe
```
## Setup
### Build
```
python -m build --wheel
```
#### Dependencies
* python >= 3
* [build](https://github.com/pypa/build)
* [installer](https://github.com/pypa/installer)
* [wheel](https://github.com/pypa/wheel)

### Install
```
python -m installer dist/*.whl
```

#### Dependencies
* python >= 3
* [pygrocy](https://github.com/SebRut/pygrocy)
* [recipe-scrapers](https://github.com/hhursev/recipe-scrapers) (If scraping a recipe doesn't work then you have to raise an issue there.)
* [texttable](https://github.com/foutaise/texttable/)
* [tomlkit](https://github.com/sdispater/tomlkit)

## Config

Most of the magic happens in the configuration file.
The script needs at least to know the names of units and potential modifiers.

The config follows the [TOML](https://toml.io/en/latest) specification and is currently hardcoded to `conversions.toml` in the script directory.

### General overview

The Grocy api endpoint is required:
``` toml
grocy_url = "https://example.com"
api_key = "asdasdasdasdasdasdasdasdasdasdasdasdasd"
api_port = 443
```

All following tables can be in a host specific or a default table.
If a value isn't found in host specific table the default table will be searched.
``` toml
[default.products]
# RecipeProduct.name = GrocyProduct
apple.name = "apples"

# overrides default
["examplerecipes.com".products]
# RecipeProduct.name = GrocyProduct
apple.name = "bananas" # this site uses apple instead of bananas
```

For all Key-Value-Pairs is the queried recipe value the key (left side) and the correct Grocy value the value (right side).

Also have a look into the `example.toml` for a complete overview.

### In-depth walkthrough

If a scraped ingredient gets parsed it will be split into segments. If a segment is already exactly present in Grocy it should find and match this entry. Otherwise each segment tries to match against some categories in the config file. If a segment isn't found here it will end up in the product name so make sure you catch all of them even if they map to the same value.

* `default_unit`:

  Default to this unit if the ingredient in the recipe doesn't have one specified.
  ``` toml
  [default]
  # default_unit = GrocyUnit
  default_unit = "Piece"
  ```

* `amounts`: "½", "¼", …

  Some special cases for declaring amount values.
  ``` toml
  [default.amounts]
  # RecipeUnit = factor
  "½" = 0.5
  "¼" = 0.25
  "⅛" = 0.125
  ```

* `modifiers`: "small", "a bit", …

  Currently this acts basically as a ignore list and will turn products without an amount into "variable" in the recipe.
  ``` toml
  [default]
  # list of modifiers to expect
  modifiers = [
      "small",
      "a bit",
      "fresh",
  ]
  ```

* `units`: "tsp", "tbsp", …
  ``` toml
  [default.units]
  # RecipeUnit.name = GrocyUnit
  tsp.name = "tea spoon"
  tbsp.name = "table spoon"
  ```

* `products`: "apple", "red onions", …

  Unmatched segments will be combined into names which can also be manipulated.
  ``` toml
  [default.products]
  # RecipeProduct.name = GrocyProduct
  apple.name = "apples"
  "red onions".name = "onions"
  ```

* `ignored_products`: "salt and pepper", …

  The resulting product can be completely ignored by this list.
  ``` toml
  [default]
  ignored_products = [
    "salt and pepper",
    "expensive sauce", # I won't use ever
  ]
  ```

* `disambiguate`:

  Another edge case is disambiguation where multiple products share the same name and are only differentiated by it's unit.
  ``` toml
  [default.disambiguate]
  # RecipeProduct.RecipeUnit = GrocyProduct
  Tomatoes.Can = "Tomatoes"
  Tomatoes.Piece = "Fresh tomatoes"
  ```

You may have noticed some of the examples used `.name` to narrow down the key-value-pair.
This is because there are some additional possible values:
* `units` can take a factor in case a unit conversion happens.
  ``` toml
  [default.units]
  # Convert given ml into liter
  # 1 ml = 0.001 l
  ml.name = "liter"
  ml.factor = 0.001
  ```
* `products` can take everything of a unit - this will take precedence when doing the conversion.
  ``` toml
  [default.products]
  water.name = "wine"
  water.unit = "tea spoon"
  water.factor = 0.5
  ```
However, these are optional and if they're properly assigned in Grocy itself then there's no need to do this here again.

If the script encounters some missing values then it will print them out and stop. At this point the recipe isn't added yet!
