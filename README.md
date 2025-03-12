## Installing

### Prerequisites

Ensure you have python, node, and npm installed.

### Backend


```bash
python3 -m venv .venv
source venv/bin/activate
pip install -r requirements.txt
```

Set up .env file: included in Document

### Frontend

```bash
npm install
```

### Running the application
To run the client, navigate to /frontend and run:

```bash
npm start
```

To run the server, navigate to /backend and run:

```bash
uvicorn app.main:app --reload
```


