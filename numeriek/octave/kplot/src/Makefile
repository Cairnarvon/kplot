.phony: all
all: kplot.oct

.phony: clean
clean:
		rm -f kplot.oct *.o

.phony: distclean
distclean: clean
		rm -f *~ octave-core core

%.oct: %.cc
		mkoctfile $<

