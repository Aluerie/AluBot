.PHONY: run
.SILENT: run
run:  # Run the bot in the subset-mode
	uv run src/main.py -t -a YENBOT
