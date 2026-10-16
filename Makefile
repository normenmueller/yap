.PHONY: test check report

test:
	PYTHONPATH=dev/src python3 -B -m unittest discover -s dev/tst -p 'test_*.py'

check report:
	@test -n "$(INSTANCE)" || (echo 'Set INSTANCE to the portfolio directory'; exit 1)
	PYTHONPATH="$(CURDIR)/dev/src" python3 -B -m yap --instance "$(INSTANCE)" $@
