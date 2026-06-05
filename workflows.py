def execute_batches(batches):
    run_batch("CATEGORY A", batches.category_a, identify_category_a)
    run_batch("CATEGORY B", batches.category_b, identify_category_b)
    run_batch("CATEGORY C", batches.category_c, identify_category_c)

    if batches.unknown:
        print("=" * 40)
        print("UNKNOWN ITEMS")
        for index, item_type, row in batches.unknown:
            print(f"Line {index + 1}: unknown item_type '{item_type}'")


def run_batch(name, rows, handler):
    if not rows:
        return

    print("=" * 40)
    print(f"STARTING {name} BATCH")

    for index, row in rows:
        handler(row)


def identify_category_a(row):
    model = normalize(row.get("model", ""))

    if model.startswith("alpha"):
        return DemoInsertActions.insert_alpha(row)
    if model.startswith("beta"):
        return DemoInsertActions.insert_beta(row)

    print(f"Category A model not mapped: {model}")


def identify_category_b(row):
    print("Category B handler placeholder")
    print(row)


def identify_category_c(row):
    print("Category C handler placeholder")
    print(row)


def normalize(value):
    return str(value).strip().lower()


class DemoInsertActions:
    @staticmethod
    def insert_alpha(row):
        print("Inserting Alpha item")
        print(f"model={row.get('model')} x={row.get('x')} y={row.get('y')}")
        print("Demo templates: demo_nav_customers.png -> demo_button_new_customer.png")

    @staticmethod
    def insert_beta(row):
        print("Inserting Beta item")
        print(f"model={row.get('model')} x={row.get('x')} y={row.get('y')}")
        print("Demo templates: demo_label_name.png -> demo_button_save_customer.png")
