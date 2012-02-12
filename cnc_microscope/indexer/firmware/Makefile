# Hmm I'm using 2231
# Other is 2211
CPU=msp430x2012
# others not supported...
#CPU=msp430x2231

CC=msp430-gcc
CFLAGS=-Os -Wall -g -mmcu=$(CPU)

OBJS=main.o

all: $(OBJS)
	$(CC) $(CFLAGS) -o main.elf $(OBJS)

%.o: %.c
	$(CC) $(CFLAGS) -c $<

clean:
	rm -fr main.elf $(OBJS)
	
download:
	mspdebug rf2500 'prog main.elf'

