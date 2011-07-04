# Quietust JSSim data toolchain
# Makefile copyright 2011 John McMaster <JohnDMcMaster@gmail.com>
# Released under 2 clause BSD license, see COPYING for details

CFLAGS=-Wall -Werror

all: qtchk qtnl

qtchk:
	g++ check.cpp $(CFLAGS) -o qtchk

qtnl:
	g++ netlist.cpp $(CFLAGS) -o qtnl
	
clean:
	rm -f qtchk qtnk *.o

