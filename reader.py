import pandas as pd


class SpreadsheetReader:
    """Reads tabular input files and groups rows by automation category."""

    REQUIRED_COLUMNS = {"item_type", "model"}

    def read(self, file_path: str) -> pd.DataFrame:
        path = str(file_path)

        if path.lower().endswith(".csv"):
            dataframe = pd.read_csv(path)
        else:
            dataframe = pd.read_excel(path)

        self.validate(dataframe)
        return dataframe

    def validate(self, dataframe: pd.DataFrame) -> None:
        missing = self.REQUIRED_COLUMNS - set(dataframe.columns)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"Missing required column(s): {missing_text}")

    def split_into_batches(self, dataframe: pd.DataFrame):
        batches = SpreadsheetBatches()

        for index, row in dataframe.iterrows():
            batches.add_row(index, row)

        return batches


class SpreadsheetBatches:
    """Stores spreadsheet rows grouped by the action family they should trigger."""

    def __init__(self):
        self.category_a = []
        self.category_b = []
        self.category_c = []
        self.unknown = []

    def add_row(self, index, row):
        item_type = str(row.get("item_type", "")).strip().lower()

        match item_type:
            case "category_a":
                self.category_a.append((index, row))
            case "category_b":
                self.category_b.append((index, row))
            case "category_c":
                self.category_c.append((index, row))
            case _:
                self.unknown.append((index, item_type, row))

    def summary(self):
        return {
            "category_a": len(self.category_a),
            "category_b": len(self.category_b),
            "category_c": len(self.category_c),
            "unknown": len(self.unknown),
        }


if __name__ == "__main__":
    from workflows import execute_batches

    reader = SpreadsheetReader()
    data = reader.read("examples/demo_items.csv")
    batches = reader.split_into_batches(data)

    print(batches.summary())
    execute_batches(batches)

