"""Comprueba el resumen anual del origen elegido desde la raíz del proyecto."""

import argparse
import json
import sys

from sqlalchemy.exc import DBAPIError

from src.data.csv_fuentes import resumen_anual_csv
from src.data.sql_server import resumen_anual_sql


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origen", choices=("sql", "csv"), required=True)
    args = parser.parse_args()
    try:
        resumen = resumen_anual_sql() if args.origen == "sql" else resumen_anual_csv()
        if not resumen:
            raise ValueError("El origen no devolvió ningún periodo.")
    except DBAPIError as error:
        print(f"Error del controlador SQL: {error.orig}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps({"origen": args.origen, "anual": resumen}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
