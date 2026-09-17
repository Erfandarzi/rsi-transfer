PY := conda run -n dify python

.PHONY: all data figures test lint arms clean

all: data figures test

data:                       ## fetch the public Harness-Bench matrix into data/raw (not committed)
	@$(PY) -c "import sys; sys.path.insert(0,'src'); \
	from pathlib import Path; from rsitransfer import harnessbench as hb; \
	[print(f'{p.asset}: {p.bytes}b sha256={p.sha256[:16]}...') for p in hb.fetch(Path('data/raw'))]"

figures: data              ## regenerate every figure from cached data (no network, no API keys)
	@$(PY) analysis/01_pilot_table6.py
	@$(PY) analysis/02_reference_class.py
	@$(PY) analysis/03_power_floor.py

test:                      ## unit tests: metric, reference estimator, ablation arm integrity
	@$(PY) -m pytest -q

lint:
	@conda run -n dify ruff check src analysis tests

arms:                      ## fetch pinned upstreams and build the ablation arms (no API calls)
	@./experiments/ablation/setup.sh
	@$(PY) experiments/ablation/make_arms.py

clean:
	@rm -rf .pytest_cache .ruff_cache src/*.egg-info
	@find . -name __pycache__ -type d -prune -exec rm -rf {} +
