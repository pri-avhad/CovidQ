#include <Wire.h>
#include "MAX30100_PulseOximeter.h"

PulseOximeter pox;
uint32_t lastReport = 0;
int oxi = 0;

void setup()
{
    Serial.begin(9600);
    if (!pox.begin()) {
        Serial.println("FAILED");
        for(;;);
    } 
     pox.setIRLedCurrent(MAX30100_LED_CURR_7_6MA);
}

void loop()
{
    pox.update();
        oxi = pox.getSpO2();
        if(oxi > 1 && oxi <= 100)
        Serial.println(oxi);
}
