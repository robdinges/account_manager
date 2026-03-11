from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from account import AccountBook, DATE_FMT


DATA_FILE = Path(__file__).with_name("accounts_data.json")


def load_payload() -> Dict:
    if not DATA_FILE.exists():
        return {"accounts": [], "operations": []}
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def build_book(payload: Dict) -> AccountBook:
    return AccountBook.from_payload(payload, verbose=False)


def get_account_labels(book: AccountBook) -> List[str]:
    labels = []
    for acc in book.accounts.values():
        labels.append(f"{acc.account_number} - {acc.owner}")
    return labels


def parse_account_number(label: str) -> str:
    return label.split(" - ", 1)[0]


def transaction_rows(account) -> List[Dict]:
    rows: List[Dict] = []
    running_balance = 0.0

    ordered = sorted(account.transactions, key=lambda tx: (tx.date, tx.sequence))
    for tx in ordered:
        if tx.transaction_type == "Initial balance":
            running_balance = tx.amount
        elif tx.transaction_type in {"Withdrawal", "Transfer out"}:
            running_balance -= tx.amount
        else:
            running_balance += tx.amount

        rows.append(
            {
                "Type": tx.transaction_type,
                "Amount": round(tx.amount, 2),
                "Date": tx.date.strftime(DATE_FMT),
                "Balance": round(running_balance, 2),
            }
        )

    return rows


def validate_operation(payload: Dict, operation: Dict) -> Tuple[bool, str]:
    op_type = operation["type"]
    amount = operation["amount"]

    if amount <= 0:
        return False, "Bedrag moet groter dan 0 zijn."

    book = build_book(payload)

    if op_type in {"deposit", "withdraw"}:
        acc_no = operation.get("account", "")
        if acc_no not in book.accounts:
            return False, f"Rekening {acc_no} bestaat niet."

    if op_type == "transfer":
        source = operation.get("from_account", "")
        target = operation.get("to_account", "")
        if source == target:
            return False, "Bron- en doelrekening mogen niet gelijk zijn."
        if source not in book.accounts:
            return False, f"Bronrekening {source} bestaat niet."
        if target not in book.accounts:
            return False, f"Doelrekening {target} bestaat niet."

    result = book.apply_operation(operation)

    if "Invalid amount" in result:
        return False, "Ongeldig bedrag of onvoldoende saldo."
    if "locked" in result.lower():
        return False, "Rekening is vergrendeld."

    return True, "Transactie is geldig."


def overview_screen(book: AccountBook) -> None:
    st.subheader("Actueel Rekeningoverzicht")

    labels = get_account_labels(book)
    if not labels:
        st.warning("Geen rekeningen gevonden in de datafile.")
        return

    selected = st.selectbox("Kies rekening", labels)
    account_no = parse_account_number(selected)
    acc = book.get_account(account_no)

    col1, col2, col3 = st.columns(3)
    col1.metric("Rekening", acc.account_number)
    col2.metric("Eigenaar", acc.owner)
    col3.metric("Actueel saldo", f"EUR {acc.balance:,.2f}")

    rows = transaction_rows(acc)
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)


def transaction_input_screen(payload: Dict, book: AccountBook) -> None:
    st.subheader("Transactie Invoeren")

    labels = get_account_labels(book)
    if not labels:
        st.warning("Geen rekeningen beschikbaar voor invoer.")
        return

    op_type = st.selectbox("Type", ["deposit", "withdraw", "transfer"])

    if op_type in {"deposit", "withdraw"}:
        account_label = st.selectbox("Rekening", labels)
        account_no = parse_account_number(account_label)
    else:
        from_label = st.selectbox("Van rekening", labels)
        to_label = st.selectbox("Naar rekening", labels)
        from_no = parse_account_number(from_label)
        to_no = parse_account_number(to_label)

    amount = st.number_input("Bedrag", min_value=0.0, step=10.0, format="%.2f")
    tx_date = st.date_input("Datum", value=date.today())

    if st.button("Opslaan transactie", type="primary"):
        operation: Dict = {
            "type": op_type,
            "amount": float(amount),
            "date": tx_date.strftime(DATE_FMT),
        }

        if op_type in {"deposit", "withdraw"}:
            operation["account"] = account_no
        else:
            operation["from_account"] = from_no
            operation["to_account"] = to_no

        is_valid, message = validate_operation(payload, operation)
        if not is_valid:
            st.error(message)
            return

        persistent_book = AccountBook.from_json(DATA_FILE, verbose=False)
        persistent_book.apply_operation(operation, persist=True)
        st.success("Transactie opgeslagen.")
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="Account Manager", layout="wide")
    st.title("Account Manager")

    payload = load_payload()
    book = build_book(payload)

    tab1, tab2 = st.tabs(["Rekeningoverzicht", "Transactie invoer"])

    with tab1:
        overview_screen(book)

    with tab2:
        transaction_input_screen(payload, book)


if __name__ == "__main__":
    main()
