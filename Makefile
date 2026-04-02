setup:
	python -m venv venv
	venv\Scripts\python.exe -m pip install -r backend/requirements.txt

backend:
	cd backend && ..\venv\Scripts\uvicorn.exe src.api:app --reload --port 8000

notebooks:
	cd backend && ..\venv\Scripts\jupyter.exe notebook
