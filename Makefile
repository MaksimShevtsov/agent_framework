.PHONY install-pre-commit:
install-pre-commit:
	@echo "Installing pre-commit hooks"
	uv run pre-commit uninstall; uv run pre-commit install

.PHONY install:
install:
	@echo "Installing dependencies"
	uv sync --all-extras
	@make install-pre-commit

.PHONY lint:
lint:
	@echo "Running linter"
	uv run pre-commit run --all-files

.PHONY run:
run:
	@echo "Running the app"
	uv run src/manage.py runserver 0.0.0.0:8000

.PHONY: shell
shell:
	uv run src/manage.py shell

.PHONY: check
check:
	@echo "Running checks"
	@echo "Checking for manage.py"
	uv run src/manage.py check
	@echo "Checking for linter errors"
	@make lint
	@echo "Checks passed"

.PHONY: showmigrations
showmigrations:
	@echo "Showing migrations"
	uv run src/manage.py showmigrations -p


.PHONY: migrations
migrations:
	@echo "Creating migrations"
	uv run src/manage.py makemigrations


.PHONY: migrations app
migrations-app:
	@echo "Creating migrations"
	@read -p "Enter app name: " app_name; \
	uv run src/manage.py makemigrations $$app_name


.PHONY: migrate
migrate:
	@echo "Applying migrations"
	uv run src/manage.py migrate

.PHONY: superuser
superuser:
	@echo "Creating superuser"
	uv run src/manage.py createsuperuser

.PHONY: test
test:
	@echo "Running tests"
	uv run src/manage.py test apps.AI

.PHONY: coverage
coverage:
	@echo "Running coverage"
	uv run coverage run src/manage.py test
	uv run coverage report

.PHONY: startapp
startapp:
	@echo "Adding app"
	@read -p "Enter app name: " app_name; \
	mkdir -p src/apps/$$app_name; \
	uv run src/manage.py startapp $$app_name src/apps/$$app_name
