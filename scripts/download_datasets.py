"""Dataset helper for Spider and WikiSQL.

Large datasets are intentionally not stored in this repository. This script
prints the expected folder layout and can process files after they are placed
locally.
"""

import json
from pathlib import Path


DATA_DIR = Path("data")
SPIDER_DIR = DATA_DIR / "spider"
WIKISQL_DIR = DATA_DIR / "wikisql" / "data"


def process_spider(limit_train: int = 1000, limit_dev: int = 100) -> None:
    train_file = SPIDER_DIR / "train_spider.json"
    dev_file = SPIDER_DIR / "dev.json"

    if not train_file.exists():
        print("Spider files were not found. Skipping Spider processing.")
        return

    with train_file.open("r", encoding="utf-8") as file:
        train_data = json.load(file)

    train_examples = [
        {"question": item["question"], "sql": item["query"]}
        for item in train_data[:limit_train]
    ]

    (DATA_DIR / "spider_train.json").write_text(
        json.dumps(train_examples, indent=2),
        encoding="utf-8",
    )

    if dev_file.exists():
        with dev_file.open("r", encoding="utf-8") as file:
            dev_data = json.load(file)

        dev_examples = [
            {"question": item["question"], "sql": item["query"]}
            for item in dev_data[:limit_dev]
        ]
        (DATA_DIR / "spider_test.json").write_text(
            json.dumps(dev_examples, indent=2),
            encoding="utf-8",
        )

    print(f"Processed {len(train_examples)} Spider training examples.")


def convert_wikisql_to_sql(sql_obj: dict) -> str:
    agg_ops = ["", "MAX", "MIN", "COUNT", "SUM", "AVG"]
    cond_ops = ["=", ">", "<", "OP"]

    agg = agg_ops[sql_obj["agg"]] if sql_obj["agg"] < len(agg_ops) else ""
    selected_column = sql_obj["sel"]

    if agg:
        sql = f"SELECT {agg}({selected_column}) FROM table"
    else:
        sql = f"SELECT {selected_column} FROM table"

    conditions = []
    for column, operator, value in sql_obj.get("conds", []):
        op = cond_ops[operator] if operator < len(cond_ops) else "="
        value_text = f"'{value}'" if isinstance(value, str) else str(value)
        conditions.append(f"{column} {op} {value_text}")

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    return sql + ";"


def process_wikisql(limit_train: int = 1000, limit_dev: int = 100) -> None:
    train_file = WIKISQL_DIR / "train.jsonl"
    dev_file = WIKISQL_DIR / "dev.jsonl"

    if not train_file.exists():
        print("WikiSQL files were not found. Skipping WikiSQL processing.")
        return

    train_examples = []
    with train_file.open("r", encoding="utf-8") as file:
        for index, line in enumerate(file):
            if index >= limit_train:
                break
            item = json.loads(line)
            train_examples.append(
                {"question": item["question"], "sql": convert_wikisql_to_sql(item["sql"])}
            )

    (DATA_DIR / "wikisql_train.json").write_text(
        json.dumps(train_examples, indent=2),
        encoding="utf-8",
    )

    if dev_file.exists():
        dev_examples = []
        with dev_file.open("r", encoding="utf-8") as file:
            for index, line in enumerate(file):
                if index >= limit_dev:
                    break
                item = json.loads(line)
                dev_examples.append(
                    {"question": item["question"], "sql": convert_wikisql_to_sql(item["sql"])}
                )

        (DATA_DIR / "wikisql_test.json").write_text(
            json.dumps(dev_examples, indent=2),
            encoding="utf-8",
        )

    print(f"Processed {len(train_examples)} WikiSQL training examples.")


def print_instructions() -> None:
    print("Dataset setup")
    print("=" * 40)
    print("Spider:")
    print("  Download from: https://github.com/taoyds/spider")
    print("  Place extracted files in: data/spider/")
    print("  Expected file: data/spider/train_spider.json")
    print()
    print("WikiSQL:")
    print("  Download from: https://github.com/salesforce/WikiSQL")
    print("  Extract data.tar.bz2 into: data/wikisql/")
    print("  Expected file: data/wikisql/data/train.jsonl")
    print()
    print("After downloading, run this script again to create:")
    print("  data/spider_train.json")
    print("  data/spider_test.json")
    print("  data/wikisql_train.json")
    print("  data/wikisql_test.json")


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    print_instructions()
    print()
    process_spider()
    process_wikisql()


if __name__ == "__main__":
    main()
