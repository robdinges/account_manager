# Account Manager

Een eenvoudige accountmanager met:

- een Python-domeinlaag (`account.py`)
- JSON-databron (`accounts_data.json`)
- Streamlit UI (`streamlit_app.py`)

## Functionaliteit

- Meerdere rekeningen beheren op basis van data in JSON.
- Transacties ondersteunen: `deposit`, `withdraw`, `transfer`.
- Actueel rekeningoverzicht tonen inclusief transactieregels.
- Basis rente-inschatting per rekening.

## Structuur

- `account.py`: businesslogica voor rekeningen en transacties.
- `accounts_data.json`: brondata (rekeningen en transactiehistorie).
- `streamlit_app.py`: webinterface voor overzicht en invoer.
- `requirements.txt`: benodigde Python-packages.

## Installatie

```bash
pip install -r requirements.txt
```

## Starten

### 1) CLI-uitvoer

```bash
python account.py
```

### 2) Streamlit-scherm

```bash
streamlit run streamlit_app.py
```

## JSON-opslag (belangrijk)

Nieuwe transacties worden direct opgeslagen in `accounts_data.json`.

- In de Streamlit UI: bij `Opslaan transactie` wordt de transactie meteen gepersist.
- In code: als je `AccountBook.from_json(...)` gebruikt en daarna `apply_operation(...)` aanroept, wordt ook direct naar dezelfde JSON-file geschreven.

Voorbeeld:

```python
from pathlib import Path
from account import AccountBook

book = AccountBook.from_json(Path("accounts_data.json"), verbose=False)
book.apply_operation({
    "type": "deposit",
    "account": "123",
    "amount": 50,
    "date": "2026-03-11"
})
```

## Opmerking

Gebruik bij voorkeur altijd de JSON als single source of truth. Pas data handmatig alleen aan als de app niet draait.
