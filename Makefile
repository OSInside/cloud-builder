buildroot = /
python_version = 3
python_lookup_name = python$(python_version)
python = $(shell which $(python_lookup_name))
docdir = /usr/share/doc/packages

version := $(shell \
	$(python) -c \
	'from cloud_builder.version import __version__; print(__version__)'\
)

tox:
	tox "-n 5"

install:
	# install license/readme
	# NOTE: this file is not handled through pip because on system level
	install -d -m 755 ${buildroot}${docdir}/python-cloud_builder
	install -m 644 LICENSE \
		${buildroot}${docdir}/python-cloud_builder/LICENSE
	install -m 644 README.rst \
		${buildroot}${docdir}/python-cloud_builder/README
	# completion
	install -d -m 755 ${buildroot}usr/share/bash-completion/completions
	install -m 755 completion/cb-ctl \
		${buildroot}usr/share/bash-completion/completions/cb-ctl

build: clean tox
	# create setup.py variant for rpm build.
	# delete module versions from setup.py for building an rpm
	# the dependencies to the python module rpm packages is
	# managed in the spec file
	sed -ie "s@>=[0-9.]*'@'@g" setup.py
	# build the sdist source tarball
	$(python) setup.py sdist
	# restore original setup.py backed up from sed
	mv setup.pye setup.py
	# provide rpm source tarball
	mv dist/cloud_builder-${version}.tar.gz \
		dist/python-cloud_builder.tar.gz
	# update rpm changelog using reference file
	helper/update_changelog.py \
		--since package/python-cloud_builder.changes \
	> dist/python-cloud_builder.changes
	helper/update_changelog.py \
		--file package/python-cloud_builder.changes \
	>> dist/python-cloud_builder.changes
	# update package version in spec file
	cat package/python-cloud_builder-spec-template |\
		sed -e s'@%%VERSION@${version}@' \
	> dist/python-cloud_builder.spec
	# provide rpm rpmlintrc
	cp package/python-cloud_builder-rpmlintrc dist

pypi: clean tox
	$(python) setup.py sdist upload

clean:
	$(python) setup.py clean
	rm -rf doc/build
	rm -rf dist/*
