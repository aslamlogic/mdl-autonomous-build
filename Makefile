test-capture:
	python capture_sink.py run --component tests --severity high -- pytest -q
