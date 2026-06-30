@echo off
echo Setting up AcuRecruit virtual environment...
python -m venv venv
call venv\Scripts\activate

echo Installing dependencies...
pip install --upgrade pip >nul
pip install -r requirements.txt

echo Seeding demo data (recruiter + job + sample resumes)...
python seed_demo.py

echo.
echo Setup complete! Starting the app now...
echo AcuRecruit is running at http://127.0.0.1:5000
echo Admin login:     admin@example.com / admin123
echo Recruiter login: recruiter@example.com / recruiter123
echo.

python app.py
