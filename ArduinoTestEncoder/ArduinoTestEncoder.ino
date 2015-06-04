

#include <PololuWheelEncoders.h>
#define pA0 4
#define pB1 5
#define pA1 6
#define pB1 7

PololuWheelEncoders enc;

void setup() {
   enc.init( pA0, pB1, pA1, pB1 );
   // place the rest of your code here !! 
} 
