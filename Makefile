include .env

# Otherwise `make scp` doesn't work, idk.
ifeq ($(OS),Windows_NT)
    SHELL := pwsh.exe
else
    SHELL := pwsh
endif
.SHELLFLAGS := -NoProfile -Command 

# Removes `make[1]: Entering directory 'D:/CODE/AluBot' messages` https://stackoverflow.com/a/71371359/19217368
# Allowing for nested makes without annoyance of that message.
MAKEFLAGS += --no-print-directory

.PHONY: run
.SILENT: run
run:  # Run the bot in the subset-mode, with test account
	uv run src/main.py --subset-mode --test-account


.PHONY: ride
.SILENT: ride
ride:  # Run the bot fully, with test account
	uv run src/main.py --test-account

.PHONY: ruff
.SILENT: ruff
ruff:  # Run the Ruff's linter 
	uv run ruff check $(sources)
	uv run ruff format --check $(sources)


.PHONY: ty
.SILENT: ty
ty:  # Run typechecker (ty)
	uv run ty check .

.PHONY: scp
.SILENT: scp
scp:  # Copy required files into the VPS
	scp -i "${SSH_PRIVATE_KEY}" .env ${SSH_USERNAME}@${SSH_HOST}:~/AluBot/.env