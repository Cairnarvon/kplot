all: verslag.pdf

verslag.pdf: verslag.tex gloss.tex
	pdflatex verslag.tex
	makeglossaries verslag
	pdflatex verslag.tex
	makeglossaries verslag
	pdflatex verslag.tex

.PHONY: clean
clean:
	rm -f *.log *.aux *.glg *.glo *.gls *.ist *.lof *.toc verslag.pdf
