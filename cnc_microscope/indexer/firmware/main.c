#include <io.h>
#include <signal.h>
#include <stdint.h>
#include <stdbool.h>
#include <limits.h>




//#include <msp430x20x2.h> 

#include "msp430x2231.h"



/*
Step order for CW is:
-4
-2
-3
-1
*/

typedef enum {
	STATE_INVALID,
	STATE_A,
	STATE_B,
	STATE_C,
	STATE_D,
} state_t;
#define STATE_MIN	STATE_A
#define STATE_MAX	STATE_D

//CW rotation
#define STATE_A_OUT		(1 << 3)
#define STATE_B_OUT		(1 << 1)
#define STATE_C_OUT		(1 << 2)
#define STATE_D_OUT		(1 << 0)


#define STEPS_INF			UINT_MAX
unsigned int g_steps_remaining = STEPS_INF;

#define     LED0                  BIT0
#define     LED1                  BIT6
#define     LED_DIR               P1DIR
#define     LED_OUT               P1OUT

#define STEPPER_PORT_DIR			P1DIR
#define STEPPER_PORT				P1OUT

volatile state_t g_state = STATE_A;
bool g_cw = false;

void initLEDs(void) {
	//LED_DIR |= LED0 + LED1;	//Set LED pins as outputs
	STEPPER_PORT_DIR |= 0xFF;
	//LED_OUT |= LED0 + LED1;	//Turn on both LEDs
}

void stop_WD() {
	/*Halt the watchdog timer
	According to the datasheet the watchdog timer
	starts automatically after powerup. It must be
	configured or halted at the beginning of code
	execution to avoid a system reset. Furthermore,
	the watchdog timer register (WDTCTL) is
	password protected, and requires the upper byte
	during write operations to be 0x5A, which is the
	value associated with WDTPW.*/
	WDTCTL = WDTPW + WDTHOLD;
}

/*
void Transmit(char c)
{
	//Get byte ready to TX
	TXByte = c;
	
	// TXD Idle as Mark
	CCTL0 = OUT;
	// SMCLK, continuous mode
	TACTL = TASSEL_2 + MC_2;

	// Load Bit counter, 8 bits + ST/SP
	BitCnt = 0xA;
	CCR0 = TAR;

	// Set time till first bit
	CCR0 += Bitime;
	// Add stop bit to TXByte (which is logical 1)
	TXByte |= 0x100;
	// Add start bit (which is logical 0)
	TXByte = TXByte << 1;

	// Set signal, intial value, enable interrupts
	CCTL0 = CCIS0 + OUTMOD0 + CCIE;
	// Wait for TX completion
	while ( CCTL0 & CCIE ) {
	}
	// SMCLK, timer off (for power consumption)
	TACTL = TASSEL_2;
}

void serial_init(void) {
	BCSCTL1 = CALBC1_1MHZ; // Set range
	DCOCTL = CALDCO_1MHZ; // SMCLK = DCO = 1MHz

	P1SEL |= TXD; //
	P1DIR |= TXD; //
}
*/


//#define printf(format, ...) uprintf(pchar1, format, ## __VA_ARGS__)


#if 0
/** Inline function to send a character to uart1.
\param c - character to send
*/
static inline void uartTx(char c) {
      while(!(IFG2 & UTXIFG1));     // wait for tx buf empty
      U1TXBUF = c;
}
/** Inline function to receive a character from uart.
Waits for a character to be available in receive buffer of uart1, then
reads and returns the character.
*/
static inline unsigned int uartRx(void) {
      while(!(IFG2 & URXIFG1));     // wait for rx buf full
      return U1RXBUF;
}

#endif


void putchar(char c) {
	while(!(IFG2 & UCA0TXIFG));

	/* wait for TX register to be empty */
	UCA0TXBUF = c;	/* send the character */
}						/* putchar */

int main(void) {
	stop_WD();

	initLEDs();

	//Set ACLK to use internal VLO (12 kHz clock)
	BCSCTL3 |= LFXT1S_2;	

	//Set TimerA to use auxiliary clock in UP mode
	//TACTL = TASSEL__ACLK | MC__UP;	
	//Set TimerA to use auxiliary clock in UP mode
	TACTL = TASSEL_1 | MC_1; 
	//Enable the interrupt for TACCR0 match
	TACCTL0 = CCIE;	
	/*Set TACCR0 which also starts the timer. At
	12 kHz, counting to 12000 should output
	an LED change every 1 second. Try this
	out and see how inaccurate the VLO can be */
	TACCR0 = 11999;
	//slow it down
	TACCR0 /= 400;
	
	printf("Hello!\n");
	
	//Enable global interrupts
	WRITE_SR(GIE);	

	while(1) {
		//Loop forever, interrupts take care of the rest
	}
}

interrupt(TIMERA0_VECTOR) TIMERA0_ISR(void) {
	//LED_OUT ^= (LED0 + LED1);	//Toggle both LEDs
	if (g_cw) {
		if (g_state == STATE_MAX) {
			g_state = STATE_MIN; 
		} else {
			++g_state;
		}
	} else {
		if (g_state == STATE_MIN) {
			g_state = STATE_MAX; 
		} else {
			--g_state;
		}
	}
	
	unsigned int mask = 0;
	switch (g_state) {
	case STATE_A:
		mask = STATE_A_OUT;
		break;
	case STATE_B:
		mask = STATE_B_OUT;
		break;
	case STATE_C:
		mask = STATE_C_OUT;
		break;
	case STATE_D:
		mask = STATE_D_OUT;
		break;
	default:
		;
	}
	STEPPER_PORT = mask;
}

