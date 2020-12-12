setup_unix:
	@python3 -m venv venv
	@source venv/bin/acivate
	@pip install -r requirements.txt

setup_win:
	@python3 -m venv venv
	venv/bin/acivate
	@pip install -r requirements.txt