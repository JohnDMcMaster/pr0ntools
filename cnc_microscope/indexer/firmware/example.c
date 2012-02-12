/******************************************************************************
* MSP-EXP430G2-LaunchPad Software UART Transmission
*
* Original Code: From MSP-EXP430G2-LaunchPad User Experience Application
* Original Author: Texas Instruments
*
* Description: This code shows the minimum neeed to send data over a software
* UART pin (P1.1). This is a highly condenced and modified version
* of the User Experience Application which comes programmed with
* the LaunchPad.
*
* Modified by Nicholas J. Conn - http://msp430launchpad.blogspot.com
* Date Modified: 07-25-10
******************************************************************************/
#include "msp430g2231.h"
#define TXD BIT1 // TXD on P1.1
#define Bitime 104 //9600 Baud, SMCLK=1MHz (1MHz/9600)=104
 
unsigned char BitCnt; // Bit count, used when transmitting byte
unsigned int TXByte; // Value sent over UART when Transmit() is called
 
// Function Definitions
void Transmit(void);
 
void main(void)
{
  WDTCTL = WDTPW + WDTHOLD; // Stop WDT
   
  unsigned int uartUpdateTimer = 10; // Loops until byte is sent
  unsigned int i = 0; // Transmit value counter
   
  BCSCTL1 = CALBC1_1MHZ; // Set range
  DCOCTL = CALDCO_1MHZ; // SMCLK = DCO = 1MHz
 
  P1SEL |= TXD; //
  P1DIR |= TXD; //
   
  __bis_SR_register(GIE); // interrupts enabled\
   
  /* Main Application Loop */
  while(1)
  {
    if ((--uartUpdateTimer == 0))
    {
      TXByte = i;
      Transmit();
       
      i++;
      uartUpdateTimer = 10;
    }
  }
}
 
// Function Transmits Character from TXByte
void Transmit()
{
  CCTL0 = OUT; // TXD Idle as Mark
  TACTL = TASSEL_2 + MC_2; // SMCLK, continuous mode
 
  BitCnt = 0xA; // Load Bit counter, 8 bits + ST/SP
  CCR0 = TAR;
   
  CCR0 += Bitime; // Set time till first bit
  TXByte |= 0x100; // Add stop bit to TXByte (which is logical 1)
  TXByte = TXByte << 1; // Add start bit (which is logical 0)
   
  CCTL0 = CCIS0 + OUTMOD0 + CCIE; // Set signal, intial value, enable interrupts
  while ( CCTL0 & CCIE ); // Wait for TX completion
  TACTL = TASSEL_2; // SMCLK, timer off (for power consumption)
}
// Timer A0 interrupt service routine
#pragma vector=TIMERA0_VECTOR
__interrupt void Timer_A (void)
{
  CCR0 += Bitime; // Add Offset to CCR0
  if ( BitCnt == 0) // If all bits TXed, disable interrupt
    CCTL0 &= ~ CCIE ;
  else
  {
    CCTL0 |= OUTMOD2; // TX Space
    if (TXByte & 0x01)
      CCTL0 &= ~ OUTMOD2; // TX Mark
    TXByte = TXByte >> 1;
    BitCnt --;
  }
}

