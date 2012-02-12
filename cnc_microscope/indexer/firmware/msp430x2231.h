#ifndef msp430x2231_h
#define msp430x2231_h

#include <msp430/usci.h>

/*
//Port P1
//Port P1 resistor enable       P1REN 027h
#define P1REN_		0x027
sfrb(P1REN, P1REN_);
//Port P1 selection             P1SEL 026h
#define P1SEL_ 		0x026
sfrb(1SEL, P1SEL_);
//Port P1 interrupt enable       P1IE 025h
#define P1IE_ 		0x025
sfrb(P1IE, P1IE_);
//Port P1 interrupt edge select P1IES 024h
#define P1IES_ 0x024
sfrb(P1IES, P1IES_);
//Port P1 interrupt flag        P1IFG 023h
#define P1IFG_ 0x023
sfrb(P1IFG, P1IFG_);
//Port P1 direction             P1DIR 022h
#define P1DIR_ 0x022
sfrb(P1DIR, P1DIR_);
//Port P1 output                P1OUT 021h
#define P1OUT_ 0x021
sfrb(P1OUT, P1OUT_);
//Port P1 input                  P1IN 020h
#define P1IN_ 0x020
sfrb(P1IN, P1IN_);
*/

//Special Function
//SFR interrupt flag 2           IFG2 003h
#define IFG2_ 0x003
sfrb(IFG2, IFG2_);
//SFR interrupt flag 1           IFG1 002h
//#define IFG1_ 0x002
//sfrb(IFG1, IFG1_);
//SFR interrupt enable 2          IE2 001h
#define IE2_ 0x001
sfrb(IE2, IE2_);
//SFR interrupt enable 1          IE1 000h
//#define IE1_ 0x000
//sfrb(IE1, IE1_);


//All the others are defined to this
#define UCA0TXIFG           (1<<1)

#endif

