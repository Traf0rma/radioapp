python -m venv .venv
.venv\Scripts\activate.bat
.venv\Scripts\python.exe -m pip install -r requirements.txt

чтобы собрать exe , в папке radio выполните команду: 
pyinstaller --onefile --name="Radio manager app" --noconsole main.py 
