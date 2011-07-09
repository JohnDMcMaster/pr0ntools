# Quietust JSSim data toolchain
# Makefile copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
# Released under 2 clause BSD license, see COPYING for details

CFLAGS=-Wall -Werror

QTDRC=qtdrc
QTNL=qtnl
EXES=$(QTDRC) $(QTNL)

all: $(EXES) example

$(QTDRC): check.cpp
	g++ check.cpp $(CFLAGS) -o $(QTDRC)

$(QTNL): netlist.cpp
	g++ netlist.cpp $(CFLAGS) -o $(QTNL)

example:
	convertsvg.php 
	
clean:
	rm -f $(EXES) *.o

