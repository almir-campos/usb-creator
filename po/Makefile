#!/usr/bin/make -f

package=usb-creator

.PHONY: all build clean update

all: build

# create mo from the po files
%.mo : %.po
	mkdir -p mo/$(subst .po,,$<)/LC_MESSAGES/
	msgfmt $< -o mo/$(subst .po,,$<)/LC_MESSAGES/$(package).mo

# generate all *.mo files
build: update $(patsubst %.po,%.mo,$(wildcard *.po))

clean:
	rm -rf mo
	# html
	(po4a --rm-translations po4a.cfg)
	rm -rf html/translated

# update *.pot and merge updates into *.po files
update:
	# update template.pot
	@ xgettext \
		--keyword=_ \
		--language=Python \
		--output=$(package).pot \
		--package-name=$(package) \
		--package-version='' \
		--from-code=UTF-8 \
		`find .. -wholename ../debian -prune -o -name '*.py' -print` && echo OK
	# get strings from package launcher (bash script)
	@ xgettext \
		--join-existing \
		--keyword=eval_gettext  \
		--language=Shell \
		--output=$(package).pot \
		--package-name=$(package) \
		--package-version='' \
		--from-code=UTF-8 \
		../usr/bin/$(package) && echo OK
	# get strings from the desktop file
	@ for LAUNCHER in `find .. -name '*.desktop'`; do \
		sed -r \
			-e '/^(Name|Comment|GenericName|Keywords)\[/d' \
			-e 's/^(Comment=|Name=|GenericName=|Keywords=)/_\1/' \
			$$LAUNCHER > $$LAUNCHER.in ; \
		intltool-extract --type=gettext/ini $$LAUNCHER.in ; \
		xgettext \
			--join-existing \
			--keyword=N_:1 \
			--output $(package).pot \
			$$LAUNCHER.in.h ; \
	done && echo OK
	# merge new strings with translations
	@ for POFILE in $(wildcard *.po); do \
		msgmerge --quiet --backup=none --update $$POFILE $(package).pot ; \
	done && echo OK
	# apply desktop file modifications
	@ for LAUNCHER in `find .. -name '*.desktop'`; do \
		intltool-merge --quiet --desktop-style . $$LAUNCHER.in $$LAUNCHER ; \
		rm $$LAUNCHER.in.h $$LAUNCHER.in ; \
	done && echo OK
	
	# temporary pot files
	@ touch pot/dummy.pot
	@ rm pot/*.pot
	# get strings from policy files
	@ for POLICY in `find ../usr/share/polkit-1/actions/ -name '*.policy'`; do \
		itstool \
		--out pot/"$${POLICY##*/}".pot \
		--its=polkit/polkit.its \
		$$POLICY; \
	done && echo "Policy pot files created"
	# create pot files from html files
	@ html2po -P en pot && echo "HTML pot files created"
	# remove headers in generated pot files before merging
	@ for POT in `find ./pot -name '*.pot'`; do \
		sed -i '1,/^$$/d' $$POT; \
	done
	@ msgcat pot/*.pot >> $(package).pot
	@ po4a po4a.cfg && echo "Po files and translations updated"
	# don't ship incomplete translations
	@ n_required=`ls en | wc -l`; \
	for dir in `echo translated/*`; do \
	    n_slides=`ls $$dir | wc -l`; \
	    [ $$n_slides != $$n_required ] && rm -rf $$dir; \
	done >/dev/null || true
	@ echo "Shipped usb-creator translations (`ls translated | wc -l`):" `ls translated`
