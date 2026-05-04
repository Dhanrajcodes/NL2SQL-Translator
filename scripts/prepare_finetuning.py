"""Prepare JSONL data for NL2SQL fine-tuning."""

import json
from pathlib import Path


DATA_DIR = Path("data")
OUTPUT_FILE = DATA_DIR / "finetuning_dataset.jsonl"


SAMPLE_EXAMPLES = [
    {
        "question": "Show all employees with salary above 50000",
        "sql": "SELECT * FROM employee WHERE salary > 50000;",
    },
    {
        "question": "List all departments",
        "sql": "SELECT * FROM department;",
    },
    {
        "question": "Find the average salary of all employees",
        "sql": "SELECT AVG(salary) FROM employee;",
    },
    {
        "question": "Count employees in each department",
        "sql": "SELECT department, COUNT(*) FROM employee GROUP BY department;",
    },
]


def load_examples() -> list[dict]:
    examples = []

    for file_name in ["spider_train.json", "wikisql_train.json"]:
        path = DATA_DIR / file_name
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            examples.extend(data)
        print(f"Loaded {len(data)} examples from {path}")

    if not examples:
        examples = SAMPLE_EXAMPLES
        print("No processed dataset found. Using sample examples.")

    return examples


def write_jsonl(examples: list[dict], output_file: Path = OUTPUT_FILE) -> None:
    output_file.parent.mkdir(exist_ok=True)

    with output_file.open("w", encoding="utf-8") as file:
        for example in examples:
            item = {
                "text": (
                    "Convert the following natural language question to SQL.\n"
                    f"Question: {example['question']}\n"
                    f"SQL: {example['sql']}"
                )
            }
            file.write(json.dumps(item) + "\n")

    print(f"Wrote {len(examples)} examples to {output_file}")


def main() -> None:
    examples = load_examples()
    write_jsonl(examples)


if __name__ == "__main__":
    main()
